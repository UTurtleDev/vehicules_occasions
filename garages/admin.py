from datetime import timedelta

from django.contrib import admin
from django.utils import timezone

from .models import Garage, GarageMembre, ParametrageComptable


class GarageMembreInline(admin.TabularInline):
    model = GarageMembre
    extra = 1


class ParametrageComptableInline(admin.StackedInline):
    model = ParametrageComptable
    extra = 0
    # Un garage n'a qu'un paramétrage : sans ce plafond, l'admin proposerait
    # d'en ajouter un second, que la contrainte OneToOne refuserait ensuite.
    max_num = 1


class EssaiActifFilter(admin.SimpleListFilter):
    title = 'Essai actif'
    parameter_name = 'essai_actif'

    def lookups(self, request, model_admin):
        return (
            ('true', 'Oui'),
            ('false', 'Non'),
        )

    def queryset(self, request, queryset):
        # Même règle que la propriété Garage.essai_actif : un essai démarré
        # il y a plus de 30 jours n'est plus actif.
        debut_minimum = timezone.now().date() - timedelta(days=30)
        if self.value() == 'true':
            return queryset.filter(date_debut_essai__gt=debut_minimum)
        elif self.value() == 'false':
            return queryset.exclude(date_debut_essai__gt=debut_minimum)


class GarageAdmin(admin.ModelAdmin):
    model = Garage

    readonly_fields = ('essai_actif',)

    list_display = ('nom', 'telephone', 'email', 'abonnement', 'essai_actif')

    fieldsets = (
        ('Garage', {'fields': ('nom',)}),
        ('Adresse', {'fields': ('adresse', 'ville', 'code_postal', 'telephone', 'email')}),
        ('Abonnement', {'fields': ('abonnement', 'date_debut_essai', 'essai_actif')}),
    )

    list_filter = ('abonnement', EssaiActifFilter)

    inlines = [GarageMembreInline, ParametrageComptableInline]


admin.site.register(Garage, GarageAdmin)
