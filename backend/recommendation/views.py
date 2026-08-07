import sys
from pathlib import Path

from django.conf import settings
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
    from recommend import get_recommendations
except Exception as erreur:
    get_recommendations = None
    ERREUR_MODELE = f'{type(erreur).__name__}: {erreur}'

TOP_K_DEFAUT = 10
TOP_K_MAX = 50


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
