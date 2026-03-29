from django.urls import path
from .views import CaretakerListView, CaretakerServiceListView

urlpatterns = [
    path('list/', CaretakerListView.as_view(), name='caretaker_list'),
    path('services/', CaretakerServiceListView.as_view(), name='caretaker_services'),
]
