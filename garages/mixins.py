from django.core.exceptions import PermissionDenied

from vehicules.models import Vehicule

from .utils import get_garage_actif, get_garage_ecriture


class GarageLectureMixin:
    """
    Queryset de Vehicule restreint à tous les garages de l'utilisateur
    connecté. Pour la consultation transversale (liste, détail, remises).
    """

    def get_queryset(self):
        return Vehicule.objects.filter(garage__in=self.request.user.garages.all())


class GarageEcritureRequisMixin:
    """
    Refuse l'accès à qui n'est pas gestionnaire du garage actif, sans rien
    dire du queryset.

    Séparé de GarageEcritureMixin parce que toutes les vues en écriture ne
    portent pas sur des véhicules : le paramétrage comptable, par exemple,
    a besoin de la même garde mais travaille sur un autre modèle.
    """

    def get_garage_actif(self):
        return get_garage_actif(self.request)

    def get_garage_ecriture(self):
        # Résolu une fois par requête : dispatch() puis get_queryset()
        # posent la même question.
        if not hasattr(self, '_garage_ecriture'):
            self._garage_ecriture = get_garage_ecriture(self.request)
        return self._garage_ecriture

    def dispatch(self, request, *args, **kwargs):
        if self.get_garage_ecriture() is None:
            raise PermissionDenied("Vous n'avez pas les droits de modification sur ce garage.")
        return super().dispatch(request, *args, **kwargs)


class GarageEcritureMixin(GarageEcritureRequisMixin):
    """
    Queryset de Vehicule restreint au seul garage actif de la session, et
    uniquement si l'utilisateur y est gestionnaire. Pour la création, la
    modification et la suppression.
    """

    def get_queryset(self):
        return Vehicule.objects.filter(garage=self.get_garage_ecriture())
