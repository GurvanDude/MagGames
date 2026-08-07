import re
import sys
import unicodedata
from pathlib import Path

import requests
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.decorators import api_view

from steam.models import SteamProfile
from library.models import OwnedGame
from library.views import synchroniserBibliotheque

from .serializers import JeuSerializer
from .models import Jeu

# Le modele vit dans backend/models_recommandation/. Ce dossier n'est pas un
# package et recommend.py fait "from two_tower import ...", un import a plat :
# il faut donc ajouter le dossier lui-meme au chemin de Python.
DOSSIER_MODELE = Path(settings.BASE_DIR) / 'models_recommandation'

if str(DOSSIER_MODELE) not in sys.path:
    sys.path.insert(0, str(DOSSIER_MODELE))

# Le modele a besoin de torch, de faiss et de ses fichiers entraines. Tant
# qu'il manque quelque chose, on garde l'erreur sous la main et on repond
# avec les jeux les plus populaires.
ERREUR_MODELE = None

try:
    from recommend import get_recommendations, get_similar_recommendations
except Exception as erreur:
    get_recommendations = None
    get_similar_recommendations = None
    ERREUR_MODELE = f'{type(erreur).__name__}: {erreur}'

TOP_K_DEFAUT = 10
TOP_K_MAX = 50

SPY_URL = 'https://steamspy.com/api.php'
CHARTS_URL = 'https://api.steampowered.com/ISteamChartsService/{}/v1/'
CLASSEMENT_LIMIT_DEFAUT = 20
CLASSEMENT_LIMIT_MAX = 100
CACHE_SECONDES = 3600

# Le filtre de la page classement repose uniquement sur le champ Jeu.genre.
GENRES_CLASSEMENT = {
    'tous': None,
    'action': 'Action',
    'aventure': 'Adventure',
    'casual': 'Casual',
    'indie': 'Indie',
    'rpg': 'RPG',
    'simulation': 'Simulation',
    'sports': 'Sports',
    'strategie': 'Strategy',
    'course': 'Racing',
    'massivement-multijoueur': 'Massively Multiplayer',
    'acces-anticipe': 'Early Access',
    'free-to-play': 'Free to Play',
}

CLASSEMENTS = {
    'joues': ('charts', 'GetMostPlayedGames'),
    'enligne': ('charts', 'GetGamesByConcurrentPlayers'),
    'proprietaires': ('spy', 'top100owned'),
}


def jeuxPossedes(profile):
    # On lit la table remplie par la page bibliotheque. Si le joueur n'y est
    # pas encore passe, on la remplit d'abord : les recommandations doivent
    # marcher meme si c'est la premiere page qu'il ouvre.
    possedes = OwnedGame.objects.filter(profile=profile).select_related('game')

    if profile.librarySyncedAt is None or not possedes.exists():
        synchronisation = synchroniserBibliotheque(profile)

        if synchronisation:
            profile.librarySyncedAt = timezone.now()
            profile.save(update_fields=['librarySyncedAt'])

        possedes = OwnedGame.objects.filter(profile=profile).select_related('game')

    return [(o.game.appid, o.playtime) for o in possedes]


def demanderAuModele(appids, tempsDeJeu, topK):
    # Une exception du modele ne doit pas faire tomber l'API : on renvoie une
    # liste vide, la vue basculera sur les jeux populaires.
    global ERREUR_MODELE

    if get_recommendations is None or not appids:
        return []

    try:
        resultat = get_recommendations(
            owned_appids=appids,
            playtimes=tempsDeJeu,
            top_k=topK,
        )
    except Exception as erreur:
        ERREUR_MODELE = f'{type(erreur).__name__}: {erreur}'
        return []

    # Le modele manipule des numpy.int64, que sqlite refuse dans un filtre __in
    return [int(a) for a in resultat or []]


def lesPlusPopulaires(exclus, topK):
    # On ecarte les jeux sans nom : ce sont les appid crees a vide (DLC, jeux
    # retires du store), ils n'ont rien a faire dans une liste affichee.
    return (Jeu.objects.using('donnees')
            .exclude(appid__in=exclus)
            .exclude(nom__isnull=True).exclude(nom='')
            .order_by('-avis_positifs')[:topK])


def dansLOrdreDuModele(appids):
    # filter(appid__in=...) ne garantit aucun ordre : sans ce reclassement, le
    # 1er choix du modele pourrait ressortir en 10e position.
    jeux = { j.appid: j for j in Jeu.objects.using('donnees').filter(appid__in=appids) }

    return [jeux[a] for a in appids if a in jeux]


# Create your views here.
@api_view(['GET'])
def getRecommendations(request):

    steamid = request.GET.get('steamid') or request.session.get('steamid')

    if steamid is None:
        return Response({ "detail" : "Connecte-toi avec Steam" }, status=401)

    profile = get_object_or_404(SteamProfile, steamid=steamid)

    try:
        topK = min(int(request.GET.get('limit', TOP_K_DEFAUT)), TOP_K_MAX)
    except ValueError:
        topK = TOP_K_DEFAUT

    possedes = jeuxPossedes(profile)

    appids = [a for a, _ in possedes]

    tempsDeJeu = { a: m for a, m in possedes }

    recommandes = demanderAuModele(appids, tempsDeJeu, topK)

    if recommandes:
        jeux = dansLOrdreDuModele(recommandes)
        origine = 'modele'
    else:
        # Pas de jeux, historique inexploitable, ou modele indisponible
        jeux = lesPlusPopulaires(appids, topK)
        origine = 'populaires'

    serializer = JeuSerializer(jeux, many=True)

    return Response({
        "origine" : origine,
        "modele_disponible" : get_recommendations is not None,
        "modele_erreur" : ERREUR_MODELE,
        "jeux_possedes" : len(appids),
        "recommendations" : serializer.data,
    })


@api_view(['GET'])
def getRelatedRecommendations(request, appid):
    steamid = request.GET.get('steamid') or request.session.get('steamid')

    if steamid is None:
        return Response({"detail": "Connecte-toi avec Steam"}, status=401)

    profile = get_object_or_404(SteamProfile, steamid=steamid)
    possedes = jeuxPossedes(profile)
    exclus = {owned_appid for owned_appid, _ in possedes}

    if get_similar_recommendations is None:
        return Response({
            "detail": "Le moteur de similarite est indisponible."
        }, status=503)

    try:
        appids = get_similar_recommendations(
            appid=appid,
            excluded_appids=exclus,
            top_k=4,
        )
    except Exception as erreur:
        return Response({
            "detail": f"Impossible de trouver des jeux similaires : {type(erreur).__name__}."
        }, status=502)

    jeux = dansLOrdreDuModele(appids)
    serializer = JeuSerializer(jeux, many=True)

    return Response({
        "appid": appid,
        "recommendations": serializer.data,
    })


def appidsSteamCharts(methode):
    reponse = requests.get(
        CHARTS_URL.format(methode),
        params={'key': settings.STEAM_API_KEY},
        timeout=30,
    )
    reponse.raise_for_status()

    return [
        (entree['appid'], entree.get('last_week_rank'))
        for entree in reponse.json()['response']['ranks']
    ]


def appidsSteamSpy(requete):
    reponse = requests.get(
        SPY_URL,
        params={'request': requete},
        timeout=30,
    )
    reponse.raise_for_status()

    return [(int(appid), None) for appid in reponse.json()]


def appidsDuClassement(classement):
    cache_key = f'top_{classement}'
    entrees = cache.get(cache_key)

    if entrees is not None:
        return entrees

    source, requete = CLASSEMENTS[classement]

    try:
        entrees = (
            appidsSteamCharts(requete)
            if source == 'charts'
            else appidsSteamSpy(requete)
        )
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None

    cache.set(cache_key, entrees, CACHE_SECONDES)
    return entrees


def identifiantGenre(label):
    normalise = unicodedata.normalize('NFKD', label)
    normalise = normalise.encode('ascii', 'ignore').decode('ascii').casefold()
    identifiant = re.sub(r'[^a-z0-9]+', '-', normalise).strip('-')
    return identifiant or 'genre'


def genresDuCatalogue():
    genres_en_cache = cache.get('classement_genres')

    if genres_en_cache is not None:
        return genres_en_cache

    options = {}

    for genre in GENRES_CLASSEMENT.values():
        if genre:
            options[identifiantGenre(genre)] = genre

    valeurs = Jeu.objects.using('donnees').values_list('genre', flat=True)

    for valeur in valeurs:
        for genre in re.split(r'[,|]', valeur or ''):
            label = genre.strip()
            if label:
                options.setdefault(identifiantGenre(label), label)

    genres = [
        {'value': 'tous', 'label': 'Tous les genres'},
        *[
            {'value': value, 'label': label}
            for value, label in sorted(options.items(), key=lambda item: item[1].casefold())
        ],
    ]

    cache.set('classement_genres', genres, CACHE_SECONDES)
    return genres


def selectionGenre(value, options):
    valeur = (value or 'tous').strip().casefold()

    for option in options:
        if valeur in {option['value'].casefold(), option['label'].casefold()}:
            return option['value'], None if option['value'] == 'tous' else option['label']

    return 'tous', None


def jeuDuGenre(jeu, genre_label):
    if genre_label is None:
        return True

    genres = [
        valeur.strip().casefold()
        for valeur in re.split(r'[,|]', jeu.genre or '')
        if valeur.strip()
    ]

    return genre_label.casefold() in genres


def jeuxDuClassement(entrees, genre_label):
    appids = [appid for appid, _ in entrees]
    jeux = {
        jeu.appid: jeu
        for jeu in Jeu.objects.using('donnees').filter(appid__in=appids)
    }

    retenus = []
    noms_vus = set()

    for appid, rang_precedent in entrees:
        jeu = jeux.get(appid)

        if jeu is None or not jeu.nom or not jeuDuGenre(jeu, genre_label):
            continue

        nom_normalise = re.sub(r'[^a-z0-9]+', ' ', jeu.nom.casefold()).strip()

        if nom_normalise in noms_vus:
            continue

        noms_vus.add(nom_normalise)
        retenus.append((jeu, rang_precedent))

    return retenus


def rendreClassement(request, classement):
    entrees = appidsDuClassement(classement)

    if entrees is None:
        return Response({
            'detail': 'Le classement est momentanement indisponible.'
        }, status=502)

    try:
        limite = min(
            int(request.GET.get('limit', CLASSEMENT_LIMIT_DEFAUT)),
            CLASSEMENT_LIMIT_MAX,
        )
    except (TypeError, ValueError):
        limite = CLASSEMENT_LIMIT_DEFAUT

    limite = max(1, limite)
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (TypeError, ValueError):
        page = 1

    genres = genresDuCatalogue()
    genre, genre_label = selectionGenre(request.GET.get('genre'), genres)
    tousLesJeux = jeuxDuClassement(entrees, genre_label)
    count = len(tousLesJeux)
    totalPages = max(1, (count + limite - 1) // limite)
    page = min(page, totalPages)
    debut = (page - 1) * limite
    retenus = tousLesJeux[debut:debut + limite]
    jeux = []

    for rang, (jeu, rang_precedent) in enumerate(retenus, debut + 1):
        ligne = JeuSerializer(jeu).data
        ligne['rang'] = rang
        ligne['rang_precedent'] = rang_precedent
        jeux.append(ligne)

    return Response({
        'classement': classement,
        'genre': genre,
        'genre_label': genre_label or 'Tous les genres',
        'genres': genres,
        'count': count,
        'page': page,
        'pages': totalPages,
        'page_size': limite,
        'games': jeux,
    })


@api_view(['GET'])
def topJoues(request):
    return rendreClassement(request, 'joues')


@api_view(['GET'])
def topEnLigne(request):
    return rendreClassement(request, 'enligne')


@api_view(['GET'])
def topProprietaires(request):
    return rendreClassement(request, 'proprietaires')
