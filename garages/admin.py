from django.contrib import admin
from .models import Garage  


class Essaie_actif(admin.SimpleListFilter):
    title = ('Essai actif')
    parameter_name = 'essai_actif'

    def lookups(self, request, model_admin):
        return (
            ('true', 'Oui'),
            ('false', 'Non'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(date_debut_essai__isnull=False)
        elif self.value() == 'false':
            return queryset.filter(date_debut_essai__isnull=True)






class GarageAdmin(admin.ModelAdmin):
    model = Garage

    readonly_fields = ('essai_actif',)

    list_display = ('nom', 'proprietaire','telephone', 'email', 'abonnement', 'essai_actif')

    fieldsets = (
        ('Garage', {'fields': ('nom', 'proprietaire')}),
        ('Adresse', {'fields': ('adresse', 'ville', 'code_postal', 'telephone', 'email')}),
        ('Abonnement', {'fields': ('abonnement', 'date_debut_essai', 'essai_actif')}),
    )

    list_filter = ('abonnement', Essaie_actif)
    




admin.site.register(Garage, GarageAdmin)