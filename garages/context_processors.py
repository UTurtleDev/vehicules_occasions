from .utils import get_garage_actif


def garage_actif(request):
    if not request.user.is_authenticated:
        return {}
    return {
        'garages_disponibles': request.user.garages.all(),
        'garage_actif': get_garage_actif(request),
    }
