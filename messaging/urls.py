from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversationViewSet, MessageViewSet, BlockUserView, ReportView, ReportViewSet

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'reports', ReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
    path('block/<int:user_id>/', BlockUserView.as_view(), name='block-user'),
    path('report/', ReportView.as_view(), name='report-user'),
]
