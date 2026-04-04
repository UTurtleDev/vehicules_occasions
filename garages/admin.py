from django.contrib import admin
from .models import Garage  

class GarageAdmin(admin.ModelAdmin):
    model = Garage

    readonly_fields = ('essai_actif',)

    list_display = ('nom', 'proprietaire','telephone', 'email', 'abonnement', 'essai_actif')

    fieldsets = (
        ('Garage', {'fields': ('nom', 'proprietaire')}),
        ('Adresse', {'fields': ('adresse', 'ville', 'code_postal', 'telephone', 'email')}),
        ('Abonnement', {'fields': ('abonnement', 'date_debut_essai', 'essai_actif')}),
    )
    




admin.site.register(Garage, GarageAdmin)