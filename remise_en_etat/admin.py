from django.contrib import admin
from .models import RemiseEnEtat
from vehicules.models import Vehicule

class RemiseEnEtatAdmin(admin.ModelAdmin):
    model = RemiseEnEtat

    list_display = ('vehicule', 'type_ree', 'description', 'montant')

    fieldsets = (
        ('Remise en etat', {'fields': ('vehicule','type_ree', 'description', 'montant')}),
    )

    search_fields = ('description', 'vehicule__marque__marque','vehicule__modele__modele')

    list_filter = ('type_ree', 'vehicule__marque__marque', 'vehicule__modele__modele', 'vehicule__garage__nom')




admin.site.register(RemiseEnEtat, RemiseEnEtatAdmin)