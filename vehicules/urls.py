from django.urls import path
from .views import ListVehiculeView, DetailVehiculeView, AjoutVehiculeView


app_name = 'vehicules'

urlpatterns = [
    path('', ListVehiculeView.as_view(), name='garages'),
    path('detail/<int:pk>/', DetailVehiculeView.as_view(), name='detail-vehicule'),
    path('ajouter/', AjoutVehiculeView.as_view(), name='ajouter-vehicule'),
]