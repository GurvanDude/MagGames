from .models import OwnedGame
from rest_framework import serializers


class OwnedGameSerializer(serializers.ModelSerializer):
    # On remonte le nom et l'image du jeu directement dans la ligne,
    # c'est plus simple a afficher cote React.
    appid = serializers.IntegerField(source='game.appid')
    name = serializers.CharField(source='game.name')
    image = serializers.URLField(source='game.image')

    class Meta:
        model = OwnedGame
        fields = ('appid', 'name', 'image', 'playtime')
