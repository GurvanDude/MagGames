"""
Appels a la Steam Web API, avec gestion de la cadence.

Trois endpoints, un par etape de la collecte :

    getAmis          GetFriendList     1 appel -> ~300 SteamID
    verifierPaquet   GetPlayerSummaries 1 appel -> 100 joueurs testes
    getJeux          GetOwnedGames     1 appel -> 1 bibliotheque

Cadences mesurees (pas theoriques) : GetFriendList tient 5/s,
GetPlayerSummaries 3/s, GetOwnedGames 8/s. Au-dela, Steam coupe les
connexions au lieu de renvoyer un 429 : c'est le compteur d'echecs de
l'appelant qui le revele, pas le limiteur.

Quota : 100 000 appels par jour et par cle, appels rates compris.
"""
import os
import threading
import time
from collections import deque
from pathlib import Path

import requests
from dotenv import load_dotenv

RACINE = Path(__file__).resolve().parent.parent
load_dotenv(RACINE / '.env')

FRIENDS_URL = 'https://api.steampowered.com/ISteamUser/GetFriendList/v1/'
SUMMARIES_URL = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/'
OWNED_URL = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/'

# GetPlayerSummaries accepte 100 SteamID par appel.
PAQUET = 100

# Sur un 429 : pause, puis reprise a une cadence plus basse.
ATTENTE_INITIALE = 30
ATTENTE_MAX = 300
FACTEUR_BAISSE = 0.7
RATE_MINIMUM = 0.5

# Fenetre sur laquelle le debit affiche est calcule.
FENETRE = 30.0


def getCle():
    return os.getenv('STEAM_API')


class Limiteur:
    """
    Bride la cadence, mesure le debit recent, et sert de frein commun a tous
    les threads quand Steam renvoie un 429.

    Le frein est partage : un 429 vise la cle, pas une requete particuliere.
    Si un seul thread patientait, les autres continueraient a consommer le
    quota et a entretenir le blocage.
    """

    def __init__(self, parSeconde):
        self.parSeconde = parSeconde
        self.intervalle = 1.0 / parSeconde
        self.verrou = threading.Lock()

        # chaque thread reserve son creneau : evite que N threads partent
        # tous en meme temps des que la voie est libre
        self.prochainCreneau = 0.0

        # instant avant lequel personne ne doit appeler
        self.repriseA = 0.0

        self.appels = 0
        self.freinages = 0
        self.recents = deque()

    def attendre(self):
        while True:
            with self.verrou:
                maintenant = time.monotonic()

                if maintenant >= self.repriseA:
                    creneau = max(maintenant, self.prochainCreneau)
                    self.prochainCreneau = creneau + self.intervalle

                    self.appels += 1
                    self.recents.append(creneau)
                    self._purger(maintenant)

                    attente = creneau - maintenant
                    break

                attente = min(self.repriseA - maintenant, 1.0)

            time.sleep(attente)

        # On dort HORS du verrou, sinon les threads feraient la queue a la
        # porte au lieu de patienter en parallele.
        if attente > 0:
            time.sleep(attente)

    def freiner(self, secondes):
        """Un 429 : tout le monde patiente, et la cadence baisse."""
        with self.verrou:
            maintenant = time.monotonic()

            # Sur un meme incident, tous les workers se prennent un 429. Si
            # chacun baissait la cadence, elle serait divisee par 0.7^N.
            dejaEnFrein = maintenant < self.repriseA

            self.repriseA = max(self.repriseA, maintenant + secondes)
            self.freinages += 1

            if not dejaEnFrein:
                self.parSeconde = max(self.parSeconde * FACTEUR_BAISSE, RATE_MINIMUM)
                self.intervalle = 1.0 / self.parSeconde

            return self.parSeconde

    def _purger(self, maintenant):
        while self.recents and maintenant - self.recents[0] > FENETRE:
            self.recents.popleft()

    def debitReel(self):
        """Appels par seconde sur les FENETRE dernieres secondes."""
        with self.verrou:
            maintenant = time.monotonic()
            self._purger(maintenant)

            if len(self.recents) < 2:
                return 0.0

            ecoule = maintenant - self.recents[0]

            return len(self.recents) / ecoule if ecoule > 0 else 0.0


def appelHttp(url, params, limiteur, timeout=15):
    """
    Appel en respectant la cadence.
    Sur un 429 : on attend, on baisse la cadence, et on reessaie.
    Retourne None si la requete echoue autrement (a retenter plus tard).
    """
    attente = ATTENTE_INITIALE

    while True:
        limiteur.attendre()

        try:
            reponse = requests.get(url, params=params, timeout=timeout)
        except requests.RequestException:
            return None

        if reponse.status_code != 429:
            return reponse

        cadence = limiteur.freiner(attente)

        print(f'  [429] pause {attente:.0f}s, cadence abaissee a {cadence:.2f}/s '
              f'(freinage n{limiteur.freinages})')

        attente = min(attente * 2, ATTENTE_MAX)


def getAmis(steamid, cle, limiteur):
    """Amis d'un joueur. None si la liste n'est pas visible."""
    reponse = appelHttp(FRIENDS_URL, {
        'key': cle,
        'steamid': steamid,
        'relationship': 'friend',
    }, limiteur)

    if reponse is None or reponse.status_code != 200:
        return None

    amis = reponse.json().get('friendslist', {}).get('friends', [])

    return [ami['steamid'] for ami in amis]


def verifierPaquet(steamids, cle, limiteur):
    """Parmi 100 SteamID au plus, ceux dont le profil est public."""
    reponse = appelHttp(SUMMARIES_URL, {
        'key': cle,
        'steamids': ','.join(steamids),
    }, limiteur)

    if reponse is None or reponse.status_code != 200:
        return []

    joueurs = reponse.json().get('response', {}).get('players', [])

    return [j['steamid'] for j in joueurs if j.get('communityvisibilitystate') == 3]


def getJeux(steamid, cle, limiteur):
    """
    Bibliotheque d'un joueur. Trois retours possibles :

        liste    la bibliotheque
        'prive'  Steam a repondu, mais le joueur cache ses jeux -> definitif
        None     l'appel a echoue -> a retenter plus tard

    La distinction compte : un profil prive ne doit plus jamais etre
    redemande, alors qu'une erreur reseau doit l'etre.

    "Profil public" et "jeux publics" sont deux reglages Steam distincts :
    un compte valide par verifie_ids.py peut refuser sa bibliotheque ici.
    """
    reponse = appelHttp(OWNED_URL, {
        'key': cle,
        'steamid': steamid,
        'include_appinfo': 1,
        'include_played_free_games': 1,
        'format': 'json',
    }, limiteur)

    if reponse is None or reponse.status_code != 200:
        return None

    try:
        contenu = reponse.json().get('response', {})
    except ValueError:
        return None

    # Sans la cle 'games', la bibliotheque est fermee (et non pas vide)
    if 'games' not in contenu:
        return 'prive'

    return contenu['games']
