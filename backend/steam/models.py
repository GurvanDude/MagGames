from django.db import models


# Create your models here.
class SteamProfile(models.Model):
    steamid = models.CharField(max_length=20, primary_key=True)
    personaName = models.CharField(max_length=200, default="", blank=False)
    avatar = models.URLField(max_length=500, default="")
    createdAt = models.DateTimeField(auto_now_add=True)
    librarySyncedAt = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.personaName
