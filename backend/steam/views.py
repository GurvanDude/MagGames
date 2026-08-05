import re
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.shortcuts import redirect
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import SteamProfile

OPENID_URL = 'https://steamcommunity.com/openid/login'

# Steam renvoie l'identite sous la forme https://steamcommunity.com/openid/id/76561198...
STEAMID_RE = re.compile(r'^https://steamcommunity\.com/openid/id/(\d{17})$')


# Create your views here.
def steamLogin(request):
    # On envoie l'utilisateur sur la page de connexion de Steam.
    # openid.return_to = l'adresse ou Steam nous le renverra apres.
    params = {
        'openid.ns': 'http://specs.openid.net/auth/2.0',
        'openid.mode': 'checkid_setup',
        'openid.return_to': request.build_absolute_uri('/api/auth/steam/callback/'),
        'openid.realm': request.build_absolute_uri('/'),
        'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
        'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select',
    }

    return redirect(OPENID_URL + '?' + urlencode(params))


def steamCallback(request):
    # Steam nous renvoie ici avec des parametres dans l'URL.
    # Comme n'importe qui peut appeler cette adresse avec le SteamID de
    # quelqu'un d'autre, on redemande a Steam si ces parametres sont vrais.
    params = request.GET.dict()
    params['openid.mode'] = 'check_authentication'

    try:
        response = requests.post(OPENID_URL, data=params, timeout=10)
    except requests.RequestException:
        return redirect(settings.FRONTEND_URL + '/?erreur=connexion')

    if 'is_valid:true' not in response.text:
        return redirect(settings.FRONTEND_URL + '/?erreur=connexion')

    match = STEAMID_RE.match(request.GET.get('openid.claimed_id', ''))

    if match is None:
        return redirect(settings.FRONTEND_URL + '/?erreur=connexion')

    steamid = match.group(1)

    if not settings.STEAM_API_KEY:
        return redirect(settings.FRONTEND_URL + '/?erreur=cle-steam')

    # On recupere le pseudo et l'avatar du joueur
    url = 'https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/'
    try:
        response = requests.get(
            url,
            params={'key': settings.STEAM_API_KEY, 'steamids': steamid},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError, KeyError):
        return redirect(settings.FRONTEND_URL + '/?erreur=api-steam')

    players = data.get('response', {}).get('players', [])

    if len(players) == 0:
        return redirect(settings.FRONTEND_URL + '/?erreur=profil-steam')

    SteamProfile.objects.update_or_create(
        steamid=steamid,
        defaults={
            'personaName': players[0]['personaname'],
            'avatar': players[0]['avatarfull'],
        }
    )

    # On garde le SteamID dans la session : c'est ce qui dit "je suis connecte"
    request.session['steamid'] = steamid

    return redirect(settings.FRONTEND_URL + '/?connecte=1')


@api_view(['GET'])
def currentProfile(request):
    steamid = request.session.get('steamid')

    if steamid is None:
        return Response({"detail": "Connecte-toi avec Steam"}, status=401)

    try:
        profile = SteamProfile.objects.get(steamid=steamid)
    except SteamProfile.DoesNotExist:
        return Response({"detail": "Profil Steam introuvable"}, status=404)

    return Response({
        "steamid": profile.steamid,
        "personaName": profile.personaName,
        "avatar": profile.avatar,
    })
