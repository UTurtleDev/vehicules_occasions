from django.shortcuts import render
from django.views.generic import ListView, DetailView, View
from django.db.models import Q

from vehicules.models import Vehicule, Marque


class ListVehiculeView(ListView):
    model = Vehicule
    template_name = 'vehicules/list_vehicules.html'
    context_object_name = 'vehicules'
    paginate_by = 20

    def get_queryset(self):
        qs = Vehicule.objects.select_related('marque', 'modele', 'garage')
        params = self.request.GET

        statut = params.get('statut')
        if statut == 'en-stock':
            qs = qs.filter(date_vente__isnull=True)
        elif statut == 'vendu':
            qs = qs.filter(date_vente__isnull=False)

        energies = params.getlist('energie')
        if energies:
            qs = qs.filter(energie__in=energies)

        marques = params.getlist('marque')
        if marques:
            qs = qs.filter(marque__pk__in=marques)

        search = params.get('q', '').strip()
        if search:
            qs = qs.filter(
                Q(marque__marque__icontains=search) |
                Q(modele__modele__icontains=search) |
                Q(immatriculation__icontains=search)
            )

        tri = params.get('tri', 'marque')
        if tri == 'date-asc':
            qs = qs.order_by('date_achat')
        elif tri == 'date-desc':
            qs = qs.order_by('-date_achat')
        else:
            qs = qs.order_by('marque__marque', 'modele__modele')

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET

        ctx['marques'] = Marque.objects.all().order_by('marque')

        ctx['energie_filters'] = [
            {
                'value': value,
                'label': label,
                'count': Vehicule.objects.filter(energie=value).count(),
            }
            for value, label in Vehicule.Energie.choices
        ]

        ctx['count_total'] = Vehicule.objects.count()
        ctx['count_stock'] = Vehicule.objects.filter(date_vente__isnull=True).count()
        ctx['count_vendu'] = Vehicule.objects.filter(date_vente__isnull=False).count()

        ctx['f_statut']   = params.get('statut', 'tous')
        ctx['f_energies'] = params.getlist('energie')
        ctx['f_marques']  = params.getlist('marque')
        ctx['f_search']   = params.get('q', '')
        ctx['f_tri']      = params.get('tri', 'marque')

        return ctx


class DetailVehiculeView(DetailView):
    model = Vehicule
    template_name = 'vehicules/detail_vehicule.html'
    context_object_name = 'vehicule'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['remises_en_etat'] = self.object.remises_en_etat.all()
        return context
