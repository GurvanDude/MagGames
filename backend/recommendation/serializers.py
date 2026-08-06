from .models import Jeu
from rest_framework import serializers


class JeuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Jeu
        fields = ('appid', 'nom', 'description', 'genre', 'categories', 'tags',
                  'date_sortie', 'prix', 'metacritic', 'avis_positifs',
                  'avis_negatifs', 'plateformes', 'image', 'developpeur',
                  'editeur', 'site_web')
