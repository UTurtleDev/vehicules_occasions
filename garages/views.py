from decimal import Decimal

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import UpdateView

from vehicules.exports import ventiler_marge

from .forms import ParametrageComptableForm
from .mixins import GarageEcritureRequisMixin
from .models import ParametrageComptable
from .utils import GARAGE_SESSION_KEY

# Marge du cas d'école affiché sur la page de paramétrage : un véhicule
# acheté 4 123 € et revendu 6 600 €.
EXEMPLE_MARGE = Decimal('2477')


@require_POST
def changer_garage(request):
    garage = get_object_or_404(request.user.garages, pk=request.POST.get('garage_id'))
    request.session[GARAGE_SESSION_KEY] = garage.id
    response = HttpResponse(status=204)
    response['HX-Refresh'] = 'true'
    return response


class ParametrageComptableView(GarageEcritureRequisMixin, UpdateView):
    """
    Comptes et taux de TVA du garage actif, utilisés par l'export comptable.

    Réservée aux gestionnaires : le mixin lève PermissionDenied avant même
    d'arriver ici pour un rôle en lecture seule.
    """

    form_class = ParametrageComptableForm
    template_name = 'garages/parametrage_comptable.html'
    success_url = reverse_lazy('garages:parametrage-comptable')

    def get_object(self, queryset=None):
        # Peut renvoyer une instance non sauvegardée : le formulaire s'affiche
        # alors avec les valeurs par défaut, et la première soumission crée
        # la ligne. Pas de get_or_create, donc pas d'écriture sur un GET.
        return ParametrageComptable.pour(self.get_garage_ecriture())

    def form_valid(self, form):
        # get_object() a pu renvoyer une instance neuve dont le garage n'est
        # pas encore fixé côté base : on le réaffecte avant de sauvegarder.
        form.instance.garage = self.get_garage_ecriture()
        messages.success(self.request, 'Paramétrage comptable enregistré.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['garage'] = self.get_garage_ecriture()

        # Exemple chiffré calculé par la fonction qui produit réellement
        # l'export : ce que la page montre ne peut donc pas mentir sur ce
        # que le fichier contiendra.
        debit, marge_ht, tva = ventiler_marge(EXEMPLE_MARGE, self.object.taux_tva)
        ctx['exemple'] = {'debit': debit, 'marge_ht': marge_ht, 'tva': tva}
        return ctx


# test #
