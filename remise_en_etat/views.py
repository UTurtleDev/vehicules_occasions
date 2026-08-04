from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView

from vehicules.models import Vehicule
from .models import RemiseEnEtat
from .forms import RemiseEnEtatForm


class AjouterRemiseEnEtatView(CreateView):
    model = RemiseEnEtat
    form_class = RemiseEnEtatForm
    template_name = 'remise_en_etat/ajouter_remise.html'

    def dispatch(self, request, *args, **kwargs):
        self.vehicule = get_object_or_404(Vehicule, pk=kwargs['vehicule_pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['vehicule'] = self.vehicule
        return context

    def form_valid(self, form):
        form.instance.vehicule = self.vehicule
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('vehicules:modifier-vehicule', kwargs={'pk': self.vehicule.pk})


class ListeRemisesView(TemplateView):
    template_name = 'remise_en_etat/liste_remises.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicule = get_object_or_404(Vehicule, pk=kwargs['vehicule_pk'])
        context['vehicule'] = vehicule
        context['remises_en_etat'] = vehicule.remises_en_etat.all()
        return context
