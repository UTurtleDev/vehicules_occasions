from django.core.exceptions import PermissionDenied

from vehicules.models import Vehicule

from .models import GarageMembre
from .utils import get_garage_actif


class GarageLectureMixin:
    """
    Queryset de Vehicule restreint à tous les garages de l'utilisateur
    connecté. Pour la consultation transversale (liste, détail, remises).
    """

    def get_queryset(self):
        return Vehicule.objects.filter(garage__in=self.request.user.garages.all())


class GarageEcritureMixin:
    """
    Queryset de Vehicule restreint au seul garage actif de la session, et
    uniquement si l'utilisateur y est gestionnaire. Pour la création, la
    modification et la suppression.
    """

    def get_garage_actif(self):
        return get_garage_actif(self.request)

    def get_garage_ecriture(self):
        garage = self.get_garage_actif()
        if garage is None:
            return None
        est_gestionnaire = GarageMembre.objects.filter(
            user=self.request.user, garage=garage, role=GarageMembre.Role.GESTIONNAIRE
        ).exists()
        return garage if est_gestionnaire else None

    def dispatch(self, request, *args, **kwargs):
        if self.get_garage_ecriture() is None:
            raise PermissionDenied("Vous n'avez pas les droits de modification sur ce garage.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Vehicule.objects.filter(garage=self.get_garage_ecriture())
