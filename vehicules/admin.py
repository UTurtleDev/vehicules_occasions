from django.contrib import admin
from .models import Vehicule, Marque, Modele

class StockFilter(admin.SimpleListFilter):
    title = ("Stock")
    parameter_name = "vendu"

    def lookups(self, request, model_admin):
        return ('stock', ('En stock')), ('vendu', ('Vendu'))

    def queryset(self, request, queryset):
        if self.value() == 'stock':
            return queryset.filter(date_vente__isnull=True)
        elif self.value() == 'vendu':
            return queryset.filter(date_vente__isnull=False)
        

class VehiculeAdmin(admin.ModelAdmin):
    model = Vehicule

    list_display = ('marque', 'modele', 'immatriculation', 'garage', 'date_achat', 'prix_achat', 'prix_vente','marge')

    readonly_fields = ('prix_achat',)

    fieldsets = (
        ('Garage', {'fields': ('garage',)}),
        ('Achat', {'fields': ('date_achat', 'vendeur', 'facture_achat', 'prix_vehicule', 'prix_enchere', 'prix_transport', 'prix_achat')}),
        ('Véhicule', {'fields': ('immatriculation', 'marque', 'modele', 'couleur', 'annee_vehicule', 'crit_air', 'kilometrage_achat', 'transmission', 'energie', 'chevaux_dine', 'chevaux_fiscaux')}),
        ('Vente', {'fields': ('date_vente', 'numero_vente', 'facture_vente', 'acheteur', 'kilometrage_vente', 'prix_vente')})    
    )

    search_fields = ('marque__marque', 'modele__modele', 'immatriculation', 'garage__nom') #garage__nom pour chercher le nom du garage (FK)
    list_filter = ('garage__nom', 'marque__marque', 'modele__modele', 'date_achat', 'date_vente', StockFilter)

    
    ordering = ('marque__marque', 'modele__modele', 'immatriculation', 'garage')

    class Media: # Ajout de js pour que le prix d'achat soit dynamique
        js = ('vehicules/js/prix_achat.js',)



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

    search_fields = ('marque__marque', 'modele')
    list_filter = ('marque__marque', 'modele',)

    ordering = ('marque__marque', 'modele')

    def nb_vehicules_modele(self, obj):
        return obj.vehicule_set.count()

    nb_vehicules_modele.short_description = 'Vehicules'


admin.site.register(Vehicule, VehiculeAdmin)
admin.site.register(Marque, MarqueAdmin)
admin.site.register(Modele, ModeleAdmin)
