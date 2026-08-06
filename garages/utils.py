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
