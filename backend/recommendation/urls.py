from django.urls import path
from . import views


urlpatterns = [
    path('api/recommendations/', views.getRecommendations, name='recommendations'),
]
