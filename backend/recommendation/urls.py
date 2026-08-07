from django.urls import path
from . import views


urlpatterns = [
    path('api/recommendations/', views.getRecommendations, name='recommendations'),
    path('api/top/joues/', views.topJoues, name='top_joues'),
    path('api/top/enligne/', views.topEnLigne, name='top_enligne'),
    path('api/top/proprietaires/', views.topProprietaires, name='top_proprietaires'),
]
