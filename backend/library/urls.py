from django.urls import path
from . import views


urlpatterns = [
    path('api/library/', views.getLibrary, name='library'),
]
