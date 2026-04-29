from django.shortcuts import render
from django.views.generic import ListView, DetailView, View

from vehicules.models import Vehicule

class ListVehiculeView(ListView):
    model = Vehicule
    template_name = 'vehicules/list_vehicules.html'
    context_object_name = 'vehicules'
    paginate_by = 2


class DetailVehiculeView(DetailView):
    model = Vehicule
    template_name = 'vehicules/detail_vehicule.html'      
    context_object_name = 'vehicule'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['remises_en_etat'] = self.object.remises_en_etat.all()
        return context
