from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PharmacistListView, PharmacyListView, PharmacyOrderViewSet, 
    PharmacyStockViewSet, AddQualificationView, PharmacistDashboardView
)

router = DefaultRouter()
router.register('orders', PharmacyOrderViewSet, basename='pharmacy_order')
router.register('stock', PharmacyStockViewSet, basename='pharmacy_stock')

urlpatterns = [
    path('', include(router.urls)),
    path('list/', PharmacyListView.as_view(), name='pharmacy_list'),
    # Alias attendu par le frontend (/pharmacy/branches/)
    path('branches/', PharmacyListView.as_view(), name='pharmacy_branches'),
    path('qualifications/add/', AddQualificationView.as_view(), name='add-qualification'),
    path('dashboard/', PharmacistDashboardView.as_view(), name='pharmacist-dashboard'),
]
