from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from .utils import GARAGE_SESSION_KEY


@require_POST
def changer_garage(request):
    garage = get_object_or_404(request.user.garages, pk=request.POST.get('garage_id'))
    request.session[GARAGE_SESSION_KEY] = garage.id
    response = HttpResponse(status=204)
    response['HX-Refresh'] = 'true'
    return response
