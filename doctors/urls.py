from django.urls import path
from .views import (
    DoctorListView,
    DoctorDetailView,
    DoctorSlotsView,
    DoctorProfileView,
    DoctorSlotListCreateView,
    DoctorSlotDetailView
)

urlpatterns = [
    # Search and List
    path('list/', DoctorListView.as_view(), name='doctor_list'),
    path('<int:pk>/', DoctorDetailView.as_view(), name='doctor_detail'),
    path('<int:doctor_id>/slots/', DoctorSlotsView.as_view(), name='doctor_slots'),
    
    # Doctor's own actions
    path('profile/', DoctorProfileView.as_view(), name='doctor_profile'),
    path('slots/', DoctorSlotListCreateView.as_view(), name='doctor_slots_list_create'),
    path('slots/<int:pk>/', DoctorSlotDetailView.as_view(), name='doctor_slot_detail'),
]
