from django.contrib import admin
from .models import Vehicule, Marque, Modele


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

    search_fields = ('marque__marque', 'modele__modele', 'immatriculation', 'garage__nom') #garage__nom pour chercher le nom du garage (FK)
    list_filter = ('garage__nom', 'marque__marque', 'modele__modele', 'date_achat', 'date_vente') #TODO: Selecteur de date
    ordering = ('marque__marque', 'modele__modele', 'immatriculation', 'garage')


    # Récupération du prix d'achat vehicule
    def prix_achat(self, obj):
        return obj.prix_vehicule + obj.prix_enchere + obj.prix_transport


class MarqueAdmin(admin.ModelAdmin):
    list_display = ('marque', 'nb_vehicules_marque')

    fieldsets = (
        ('Marque', {'fields': ('marque',)}),
    )

    ordering = ('marque',)

    def nb_vehicules_marque(self, obj):
        return obj.vehicule_set.count()

    nb_vehicules_marque.short_description = 'Vehicules'


class ModeleAdmin(admin.ModelAdmin):
    list_display = ('marque__marque', 'modele', 'nb_vehicules_modele')

    fieldsets = (
        ('Modele', {'fields': ('marque', 'modele')}),
    )

    ordering = ('marque__marque', 'modele')

    def nb_vehicules_modele(self, obj):
        return obj.vehicule_set.count()

    nb_vehicules_modele.short_description = 'Vehicules'


admin.site.register(Vehicule, VehiculeAdmin)
admin.site.register(Marque, MarqueAdmin)
admin.site.register(Modele, ModeleAdmin)
