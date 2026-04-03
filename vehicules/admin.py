from django.contrib import admin
from .models import Vehicule


class VehiculeAdmin(admin.ModelAdmin):
    model = Vehicule

    list_display = ('marque', 'modele', 'immatriculation', 'garage', 'date_achat', 'prix_achat', 'prix_vente','marge')

    fieldsets = (
        ('Garage', {'fields': ('garage',)}),
        #TODO: Rajouter le prix_achat
        # ('Achat', {'fields': ('date_achat', 'vendeur', 'facture_achat', 'prix_vehicule', 'prix_enchere', 'prix_transport', 'prix_achat')}),
        ('Achat', {'fields': ('date_achat', 'vendeur', 'facture_achat', 'prix_vehicule', 'prix_enchere', 'prix_transport',)}),
        ('Véhicule', {'fields': ('immatriculation', 'marque', 'modele', 'couleur', 'annee_vehicule', 'transmission', 'energie', 'chevaux_dine', 'chevaux_fiscaux')}),
        ('Vente', {'fields': ('date_vente', 'numero_vente', 'facture_vente', 'acheteur', 'prix_vente')})    
    )

    search_fields = ('marque', 'modele', 'immatriculation', 'garage__nom') #garage__nom pour chercher le nom du garage (FK)
    list_filter = ('garage__nom', 'marque', 'modele', 'date_achat', 'date_vente') #TODO: Selecteur de date
    ordering = ('marque', 'modele', 'immatriculation', 'garage')


    # Récupération du prix d'achat vehicule
    def prix_achat(self, obj):
        return obj.prix_vehicule + obj.prix_enchere + obj.prix_transport



admin.site.register(Vehicule, VehiculeAdmin)
