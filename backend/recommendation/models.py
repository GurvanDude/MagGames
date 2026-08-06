from django.db import models


# Create your models here.
# Le catalogue complet, avec description, tags, prix et image.
# managed = False : la table vit dans data/maggames.db, remplie par les
# scripts de collecte. Django la lit mais ne la cree ni ne la migre, et
# toutes les requetes passent par .using('donnees').
class Jeu(models.Model):
    appid = models.IntegerField(primary_key=True)
    nom = models.TextField(null=True)
    description = models.TextField(null=True)
    date_sortie = models.TextField(null=True)
    prix = models.FloatField(null=True)
    developpeur = models.TextField(null=True)
    editeur = models.TextField(null=True)
    genre = models.TextField(null=True)
    categories = models.TextField(null=True)
    tags = models.TextField(null=True)
    plateformes = models.TextField(null=True)
    metacritic = models.IntegerField(null=True)
    avis_positifs = models.IntegerField(null=True)
    avis_negatifs = models.IntegerField(null=True)
    image = models.TextField(null=True)
    site_web = models.TextField(null=True)

    class Meta:
        managed = False
        db_table = 'jeux'

    def __str__(self):
        return self.nom or str(self.appid)
