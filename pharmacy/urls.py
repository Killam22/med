from django.urls import path
from .views import PharmacyListView, PharmacyBranchListView

urlpatterns = [
    path('list/', PharmacyListView.as_view(), name='pharmacy_list'),
    path('branches/', PharmacyBranchListView.as_view(), name='pharmacy_branches'),
]
