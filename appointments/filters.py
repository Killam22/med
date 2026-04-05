"""Filters for the doctor search endpoint."""

import django_filters
from django.db.models import Q
from doctors.models import Doctor


class DoctorFilter(django_filters.FilterSet):
    """
    Filtres disponibles pour la recherche de médecins.
    Tous les filtres sont optionnels et combinables librement.
    """

    # Barre de recherche textuelle (nom, prénom, clinique, spécialité)
    search = django_filters.CharFilter(method='filter_search', label='Recherche libre')

    # Filtres précis
    specialty = django_filters.CharFilter(field_name='specialty', lookup_expr='exact')
    city = django_filters.CharFilter(field_name='user__city', lookup_expr='icontains')
    gender = django_filters.CharFilter(field_name='user__sex', lookup_expr='exact')

    # Note minimale
    rating_min = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')

    # Disponibilité sur une date donnée
    date = django_filters.DateFilter(method='filter_by_date', label='Date disponible')

    class Meta:
        model = Doctor
        fields = ['specialty', 'city', 'gender', 'rating_min', 'search', 'date']

    def filter_search(self, queryset, name, value):
        """Recherche dans nom, prénom, clinique et spécialité."""
        return queryset.filter(
            Q(user__first_name__icontains=value) |
            Q(user__last_name__icontains=value) |
            Q(clinic_name__icontains=value) |
            Q(specialty__icontains=value)
        )

    def filter_by_date(self, queryset, name, value):
        """Garde uniquement les médecins ayant au moins un créneau libre ce jour-là."""
        return queryset.filter(
            slots__date=value,
            slots__is_booked=False
        ).distinct()
