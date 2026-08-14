from django.urls import path
from .views import (
    ListVehiculeView, DetailVehiculeView, AjoutVehiculeView,
    ModifierVehiculeView, VendreVehiculeView, TableauDeBordView,
    ExportsView, ExportSynthesePdfView, ExportStockPdfView, ExportComptableCsvView,
)


app_name = 'vehicules'

urlpatterns = [
    path('', ListVehiculeView.as_view(), name='garages'),
    path('tableau-de-bord/', TableauDeBordView.as_view(), name='tableau-de-bord'),
    path('detail/<int:pk>/', DetailVehiculeView.as_view(), name='detail-vehicule'),
    path('ajouter/', AjoutVehiculeView.as_view(), name='ajouter-vehicule'),
    path('modifier/<int:pk>/', ModifierVehiculeView.as_view(), name='modifier-vehicule'),
    path('vendre/<int:pk>/', VendreVehiculeView.as_view(), name='vendre-vehicule'),
    path('exports/', ExportsView.as_view(), name='exports'),
    path('exports/synthese.pdf', ExportSynthesePdfView.as_view(), name='export-synthese-pdf'),
    path('exports/stock.pdf', ExportStockPdfView.as_view(), name='export-stock-pdf'),
    path('exports/comptable.csv', ExportComptableCsvView.as_view(), name='export-comptable-csv'),
]
