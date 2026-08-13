from .models import GarageMembre

GARAGE_SESSION_KEY = 'garage_actif_id'


def get_garage_actif(request):
    """
    Résout le garage actif de l'utilisateur à partir de la session.

    Retombe silencieusement sur le premier garage de l'utilisateur si la
    session est vide, ou si l'ID qu'elle contient ne correspond plus à un
    garage lui appartenant (garage supprimé ou transféré entre-temps).
    """
    if not request.user.is_authenticated:
        return None

    garages_utilisateur = request.user.garages.all()
    garage_id = request.session.get(GARAGE_SESSION_KEY)

    garage = None
    if garage_id is not None:
        garage = garages_utilisateur.filter(id=garage_id).first()

    if garage is None:
        garage = garages_utilisateur.first()
        if garage is not None:
            request.session[GARAGE_SESSION_KEY] = garage.id

    return garage


def get_role_garage_actif(request, garage=None):
    """Rôle de l'utilisateur sur le garage actif, ou None s'il n'y est pas membre."""
    if garage is None:
        garage = get_garage_actif(request)
    if garage is None:
        return None
    membre = GarageMembre.objects.filter(user=request.user, garage=garage).first()
    return membre.role if membre else None


def get_garage_ecriture(request):
    """
    Garage actif si l'utilisateur y est gestionnaire, None sinon.

    Source de vérité unique du droit d'écriture : utilisée à la fois par
    GarageEcritureMixin pour autoriser les vues, et par le context processor
    pour n'afficher les boutons d'action qu'à ceux qui peuvent s'en servir.
    Les deux ne peuvent donc pas diverger.
    """
    garage = get_garage_actif(request)
    if garage is None:
        return None
    est_gestionnaire = get_role_garage_actif(request, garage) == GarageMembre.Role.GESTIONNAIRE
    return garage if est_gestionnaire else None
