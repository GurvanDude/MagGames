import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination

from steam.models import SteamProfile

from .serializers import OwnedGameSerializer
from .filters import OwnedGameFilter
from .models import Game, OwnedGame

# L'image du jeu n'est pas donnee par l'API, mais son adresse se construit
# toujours pareil a partir de l'appid.
IMAGE_URL = 'https://cdn.cloudflare.steamstatic.com/steam/apps/{}/header.jpg'


# Create your views here.
@api_view(['GET'])
def getLibrary(request):

    steamid = request.session.get('steamid')

    if steamid is None:
        return Response({ "detail" : "Connecte-toi avec Steam" }, status=401)

    profile = get_object_or_404(SteamProfile, steamid=steamid)

    # On demande a Steam la liste des jeux du joueur
    url = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/'

    data = requests.get(url, params={
        'key': settings.STEAM_API_KEY,
        'steamid': steamid,
        'include_appinfo': 1,
        'include_played_free_games': 1,
        'format': 'json',
    }).json()

    # Steam ne renvoie rien si le profil est prive
    if 'games' not in data['response']:
        return Response({
            "detail" : "Ta bibliotheque est privee. Passe 'Details du jeu' sur 'Public' dans les parametres Steam."
        }, status=403)

    # On enregistre les jeux en base
    for jeu in data['response']['games']:
        game, created = Game.objects.update_or_create(
            appid=jeu['appid'],
            defaults={
                'name': jeu.get('name', ''),
                'image': IMAGE_URL.format(jeu['appid']),
            }
        )

        OwnedGame.objects.update_or_create(
            profile=profile,
            game=game,
            defaults={ 'playtime': jeu.get('playtime_forever', 0) }
        )

    # Puis on les relit depuis la base, comme pour les produits du eshop
    filterset = OwnedGameFilter(request.GET, queryset=OwnedGame.objects.filter(profile=profile).order_by('-playtime'))

    resPerPage = 20

    paginator = PageNumberPagination()

    paginator.page_size = resPerPage

    queryset = paginator.paginate_queryset(filterset.qs, request)

    serializer = OwnedGameSerializer(queryset, many=True)

    return Response({ "games" : serializer.data })
