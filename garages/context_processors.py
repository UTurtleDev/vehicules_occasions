from .models import GarageMembre
from .utils import get_garage_actif, get_role_garage_actif


def garage_actif(request):
    if not request.user.is_authenticated:
        return {}
    actif = get_garage_actif(request)
    role_actif = get_role_garage_actif(request, actif)
    return {
        'garages_disponibles': request.user.garages.all(),
        'garage_actif': actif,
        'role_garage_actif': role_actif,
        # Garage sur lequel les boutons d'action ont le droit de s'afficher.
        # Même règle que GarageEcritureMixin, via garages.utils.
        'garage_ecriture': actif if role_actif == GarageMembre.Role.GESTIONNAIRE else None,
    }
