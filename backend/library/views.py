from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from html import unescape
import re

import requests
from django.conf import settings
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination

from steam.models import SteamProfile
from recommendation.models import Jeu

from .serializers import OwnedGameSerializer
from .filters import OwnedGameFilter
from .models import Game, OwnedGame

# GetOwnedGames ne donne pas l'adresse de la jaquette : on la demande a la
# fiche du store.
STORE_URL = 'https://store.steampowered.com/api/appdetails'

# Dernier recours si la fiche ne repond pas. Attention, ce schema ne marche
# plus pour les jeux recents, dont l'adresse contient un hash.
IMAGE_URL = 'https://cdn.cloudflare.steamstatic.com/steam/apps/{}/header.jpg'
LIBRARY_CACHE_DURATION = timedelta(minutes=5)
DETAILS_URL = 'https://store.steampowered.com/api/appdetails'
ACHIEVEMENTS_URL = 'https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/'


def steamidPourRequete(request):
    return request.GET.get('steamid') or request.session.get('steamid')


def imageDuJeu(appid):
    # Un appel par jeu, le store n'accepte pas plusieurs appid a la fois.
    # On ne le fait donc que si aucune adresse n'est deja en base.
    try:
        response = requests.get(STORE_URL, params={'appids': appid}, timeout=5)
        response.raise_for_status()
        entry = response.json().get(str(appid)) or {}
    except (requests.RequestException, ValueError, AttributeError):
        return ''

    if not entry.get('success'):
        return ''

    return (entry.get('data') or {}).get('header_image', '')


def imagesDesJeux(appids):
    """Recupere les jaquettes manquantes en parallele."""
    if not appids:
        return {}

    with ThreadPoolExecutor(max_workers=min(8, len(appids))) as executor:
        images = executor.map(imageDuJeu, appids)
        return dict(zip(appids, images))


def texteSteam(value):
    return unescape(re.sub(r'<[^>]+>', ' ', value or '')).strip()


def valeursCatalogue(value):
    return [
        item.strip()
        for item in re.split(r'[|,]', value or '')
        if item.strip()
    ]


def detailsDepuisCatalogue(owned_game):
    catalogue = Jeu.objects.using('donnees').filter(
        appid=owned_game.game.appid
    ).first()

    if catalogue is None:
        return None

    return Response({
        'appid': owned_game.game.appid,
        'name': catalogue.nom or owned_game.game.name,
        'image': catalogue.image or owned_game.game.image,
        'description': texteSteam(catalogue.description),
        'release_date': catalogue.date_sortie or None,
        'genres': valeursCatalogue(catalogue.genre),
        'developers': [catalogue.developpeur] if catalogue.developpeur else [],
        'publishers': [catalogue.editeur] if catalogue.editeur else [],
        'categories': valeursCatalogue(catalogue.categories),
        'platforms': valeursCatalogue(catalogue.plateformes),
        'website': catalogue.site_web or None,
        'playtime': owned_game.playtime,
        'achievements': {'obtained': None, 'total': None},
    })


def synchroniserBibliotheque(profile):
    """
    Demande la bibliotheque du joueur a Steam et l'enregistre en base.

    Retourne True si ca a marche, False si le joueur cache ses jeux.
    """
    url = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/'

    try:
        response = requests.get(url, params={
            'key': settings.STEAM_API_KEY,
            'steamid': profile.steamid,
            'include_appinfo': 1,
            'include_played_free_games': 1,
            'format': 'json',
        }, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return None

    # Steam ne renvoie rien si le profil est prive
    if 'games' not in data.get('response', {}):
        return False

    appids = [jeu['appid'] for jeu in data['response']['games']]
    connues = {
        game.appid: game.image
        for game in Game.objects.filter(appid__in=appids)
    }
    images_manquantes = imagesDesJeux([
        appid for appid in appids if not connues.get(appid)
    ])

    for jeu in data['response']['games']:
        appid = jeu['appid']
        image = connues.get(appid) or images_manquantes.get(appid) or IMAGE_URL.format(appid)

        game, created = Game.objects.update_or_create(
            appid=appid,
            defaults={
                'name': jeu.get('name', ''),
                'image': image,
            }
        )

        playtime = jeu.get('playtime_forever')
        defaults = {
            'playtime': int(playtime),
        } if playtime is not None else {}

        OwnedGame.objects.update_or_create(
            profile=profile,
            game=game,
            defaults=defaults,
        )

    return True


# Create your views here.
@api_view(['GET'])
def getLibrary(request):

    steamid = steamidPourRequete(request)

    if steamid is None:
        return Response({ "detail" : "Connecte-toi avec Steam" }, status=401)

    profile = get_object_or_404(SteamProfile, steamid=steamid)

    cache_valide = (
        profile.librarySyncedAt is not None
        and timezone.now() - profile.librarySyncedAt < LIBRARY_CACHE_DURATION
    )
    force_refresh = request.GET.get('refresh') == '1'

    if cache_valide and not force_refresh:
        synchronisation = True
    else:
        synchronisation = synchroniserBibliotheque(profile)

        if synchronisation:
            profile.librarySyncedAt = timezone.now()
            profile.save(update_fields=['librarySyncedAt'])

    if synchronisation is None:
        return Response({
            "detail": "Impossible de recuperer la bibliotheque depuis Steam."
        }, status=502)

    if not synchronisation:
        return Response({
            "detail" : "Ta bibliotheque est privee. Passe 'Details du jeu' sur 'Public' dans les parametres Steam."
        }, status=403)

    # Puis on les relit depuis la base, comme pour les produits du eshop
    owned_games = OwnedGame.objects.filter(profile=profile).select_related('game')
    total_playtime = owned_games.aggregate(total=Sum('playtime'))['total'] or 0
    total_count = owned_games.count()
    filterset = OwnedGameFilter(request.GET, queryset=owned_games.order_by('-playtime'))

    resPerPage = 20

    paginator = PageNumberPagination()

    paginator.page_size = resPerPage

    queryset = paginator.paginate_queryset(filterset.qs, request)

    serializer = OwnedGameSerializer(queryset, many=True)

    return Response({
        "games" : serializer.data,
        "count": paginator.page.paginator.count,
        "total_count": total_count,
        "total_playtime": total_playtime,
        "page": paginator.page.number,
        "total_pages": paginator.page.paginator.num_pages,
        "next": paginator.get_next_link(),
        "previous": paginator.get_previous_link(),
    })


@api_view(['GET'])
def getGameDetails(request, appid):
    steamid = steamidPourRequete(request)

    if steamid is None:
        return Response({"detail": "Connecte-toi avec Steam"}, status=401)

    profile = get_object_or_404(SteamProfile, steamid=steamid)
    owned_game = get_object_or_404(
        OwnedGame.objects.select_related('game'),
        profile=profile,
        game__appid=appid,
    )

    try:
        response = requests.get(
            DETAILS_URL,
            params={'appids': appid, 'l': 'english'},
            timeout=8,
        )
        response.raise_for_status()
        entry = response.json().get(str(appid)) or {}
    except (requests.RequestException, ValueError, AttributeError):
        fallback = detailsDepuisCatalogue(owned_game)
        if fallback is not None:
            return fallback

        return Response({
            "detail": "Impossible de recuperer les details du jeu depuis Steam."
        }, status=502)

    if not entry.get('success'):
        fallback = detailsDepuisCatalogue(owned_game)
        if fallback is not None:
            return fallback

        return Response({
            "detail": "Steam ne fournit pas les details de ce jeu."
        }, status=404)

    data = entry.get('data') or {}
    player_achievements = None

    try:
        achievements_response = requests.get(
            ACHIEVEMENTS_URL,
            params={
                'key': settings.STEAM_API_KEY,
                'steamid': profile.steamid,
                'appid': appid,
                'l': 'english',
            },
            timeout=5,
        )
        if achievements_response.ok:
            achievements_data = achievements_response.json().get('playerstats') or {}
            achievements = achievements_data.get('achievements')
            if isinstance(achievements, list):
                player_achievements = sum(
                    achievement.get('achieved') == 1
                    for achievement in achievements
                )
    except (requests.RequestException, ValueError, AttributeError):
        pass

    release_date = data.get('release_date') or {}
    achievements_data = data.get('achievements') or {}
    platforms = data.get('platforms') or {}
    genres = data.get('genres') or []
    categories = data.get('categories') or []

    return Response({
        "appid": appid,
        "name": data.get('name') or owned_game.game.name,
        "image": data.get('header_image') or owned_game.game.image,
        "description": texteSteam(data.get('short_description')),
        "release_date": release_date.get('date') or None,
        "genres": [genre.get('description') for genre in genres if genre.get('description')],
        "developers": data.get('developers') or [],
        "publishers": data.get('publishers') or [],
        "categories": [category.get('description') for category in categories if category.get('description')],
        "platforms": [platform for platform, enabled in platforms.items() if enabled],
        "website": data.get('website') or None,
        "playtime": owned_game.playtime,
        "achievements": {
            "obtained": player_achievements,
            "total": achievements_data.get('total'),
        },
    })
