import django_filters
from django.db.models import Q
from .models import Doctor

class DoctorFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search', label='Recherche libre')
    specialty = django_filters.CharFilter(field_name='specialty', lookup_expr='exact')
    city = django_filters.CharFilter(field_name='exercises__est_city', lookup_expr='icontains')
    gender = django_filters.CharFilter(field_name='user__sex', lookup_expr='exact')
    rating_min = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    date = django_filters.DateFilter(method='filter_by_date', label='Date disponible')

    class Meta:
        model = Doctor
        fields = ['specialty', 'city', 'gender', 'rating_min', 'search', 'date']

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(user__first_name__icontains=value) |
            Q(user__last_name__icontains=value) |
            Q(clinic_name__icontains=value) |
            Q(specialty__icontains=value)
        )

    def filter_by_date(self, queryset, name, value):
        return queryset.filter(
            slots__date=value,
            slots__is_booked=False
        ).distinct()
