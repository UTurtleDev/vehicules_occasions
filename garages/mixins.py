from vehicules.models import Vehicule

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
    Queryset de Vehicule restreint au seul garage actif de la session.
    Pour la création, la modification et la suppression.
    """

    def get_garage_actif(self):
        return get_garage_actif(self.request)

    def get_queryset(self):
        garage = self.get_garage_actif()
        if garage is None:
            return Vehicule.objects.none()
        return Vehicule.objects.filter(garage=garage)
