from django_filters import rest_framework as filters
from .models import OwnedGame


class OwnedGameFilter(filters.FilterSet):

    keyword = filters.CharFilter(field_name='game__name', lookup_expr='icontains')
    min_playtime = filters.NumberFilter(field_name='playtime', lookup_expr='gte')
    max_playtime = filters.NumberFilter(field_name='playtime', lookup_expr='lte')

    class Meta:
        model = OwnedGame
        fields = ('keyword', 'min_playtime', 'max_playtime')
