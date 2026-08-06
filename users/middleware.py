from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponse


class HtmxLoginRedirectMiddleware:
    """
    Sans ça, une requête HTMX vers une vue protégée dont la session a expiré
    reçoit un 302 vers LOGIN_URL, et HTMX injecte la landing entière dans le
    fragment ciblé. On la transforme en 204 + HX-Redirect pour forcer un
    vrai rechargement de page côté navigateur.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.headers.get('HX-Request') != 'true':
            return response

        if response.status_code not in (301, 302):
            return response

        redirect_path = urlsplit(response.url).path
        login_path = urlsplit(settings.LOGIN_URL).path

        if redirect_path != login_path:
            return response

        htmx_response = HttpResponse(status=204)
        htmx_response['HX-Redirect'] = settings.LOGIN_URL
        return htmx_response
