from django.urls import path
from . import views


urlpatterns = [
    path('api/auth/steam/login/', views.steamLogin, name='steam_login'),
    path('api/auth/steam/callback/', views.steamCallback, name='steam_callback'),
]
