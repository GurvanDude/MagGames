from django.db import models

from steam.models import SteamProfile


# Create your models here.
class Game(models.Model):
    appid = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=300, default="", blank=False)
    image = models.URLField(max_length=500, default="")

    def __str__(self):
        return self.name


class OwnedGame(models.Model):
    profile = models.ForeignKey(SteamProfile, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    playtime = models.IntegerField(default=0)  # en minutes, comme Steam

    def __str__(self):
        return self.game.name
