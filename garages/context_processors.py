from .models import GarageMembre
from .utils import get_garage_actif


def garage_actif(request):
    if not request.user.is_authenticated:
        return {}
    actif = get_garage_actif(request)
    role_actif = None
    if actif is not None:
        membre = GarageMembre.objects.filter(user=request.user, garage=actif).first()
        role_actif = membre.role if membre else None
    return {
        'garages_disponibles': request.user.garages.all(),
        'garage_actif': actif,
        'role_garage_actif': role_actif,
    }
