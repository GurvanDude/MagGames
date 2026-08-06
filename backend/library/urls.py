from django.urls import path
from . import views


urlpatterns = [
    path('api/library/', views.getLibrary, name='library'),
    path('api/library/<int:appid>/', views.getGameDetails, name='game_details'),
]
