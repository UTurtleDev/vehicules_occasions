from django.urls import path
from .views import (
    ListVehiculeView, DetailVehiculeView, AjoutVehiculeView,
    ModifierVehiculeView, VendreVehiculeView,
)


app_name = 'vehicules'

urlpatterns = [
    path('', ListVehiculeView.as_view(), name='garages'),
    path('detail/<int:pk>/', DetailVehiculeView.as_view(), name='detail-vehicule'),
    path('ajouter/', AjoutVehiculeView.as_view(), name='ajouter-vehicule'),
    path('modifier/<int:pk>/', ModifierVehiculeView.as_view(), name='modifier-vehicule'),
    path('vendre/<int:pk>/', VendreVehiculeView.as_view(), name='vendre-vehicule'),
]