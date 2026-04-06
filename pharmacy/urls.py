from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PharmacyListView, PharmacyBranchListView, PharmacyOrderViewSet, PharmacyStockViewSet

router = DefaultRouter()
router.register('orders', PharmacyOrderViewSet, basename='pharmacy_order')
router.register('stock', PharmacyStockViewSet, basename='pharmacy_stock')

urlpatterns = [
    path('', include(router.urls)),
    path('list/', PharmacyListView.as_view(), name='pharmacy_list'),
    path('branches/', PharmacyBranchListView.as_view(), name='pharmacy_branches'),
]
