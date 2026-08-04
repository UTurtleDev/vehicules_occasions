from django.urls import path
from .views import AjouterRemiseEnEtatView, ListeRemisesView


app_name = 'remise_en_etat'

urlpatterns = [
    path('ajouter/<int:vehicule_pk>/', AjouterRemiseEnEtatView.as_view(), name='ajouter-remise'),
    path('liste/<int:vehicule_pk>/', ListeRemisesView.as_view(), name='liste-remises'),
]
