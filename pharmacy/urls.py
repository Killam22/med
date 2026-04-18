from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PharmacistListView, PharmacyListView, PharmacyOrderViewSet, PharmacyStockViewSet, AddQualificationView

router = DefaultRouter()
router.register('orders', PharmacyOrderViewSet, basename='pharmacy_order')
router.register('stock', PharmacyStockViewSet, basename='pharmacy_stock')

urlpatterns = [
    path('', include(router.urls)),
    path('list/', PharmacyListView.as_view(), name='pharmacy_list'),
    path('branches/', PharmacyListView.as_view(), name='pharmacy_branches'),
    path('qualifications/add/', AddQualificationView.as_view(), name='add-qualification'),
]
