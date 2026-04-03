from django.contrib import admin
from .models import Garage  

class GarageAdmin(admin.ModelAdmin):
    model = Garage

    list_display = ('nom', 'proprietaire','telephone', 'email', 'abonnement')

    fieldsets = (
        ('Garage', {'fields': ('nom', 'proprietaire')}),
        ('Adresse', {'fields': ('adresse', 'ville', 'code_postal', 'telephone', 'email')}),
        ('Abonnement', {'fields': ('abonnement',)}),
    )

admin.site.register(Garage, GarageAdmin)