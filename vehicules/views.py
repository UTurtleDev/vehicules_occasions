from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView
from django.db.models import Q

from vehicules.models import Vehicule, Marque, Modele
from vehicules.forms import VehiculeForm


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


class AjoutVehiculeView(CreateView):
    model = Vehicule
    form_class = VehiculeForm
    template_name = 'vehicules/ajouter_vehicule.html'

    def get_success_url(self):
        return reverse_lazy('vehicules:detail-vehicule', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['marques'] = Marque.objects.order_by('marque')
        context['modeles'] = Modele.objects.select_related('marque').order_by('marque__marque', 'modele')
        return context

    def form_valid(self, form):
        nouvelle_marque = form.cleaned_data.get('nouvelle_marque', '').strip()
        nouveau_modele = form.cleaned_data.get('nouveau_modele', '').strip()

        if nouvelle_marque:
            marque, _ = Marque.objects.get_or_create(marque=nouvelle_marque)
            form.instance.marque = marque
        else:
            marque = form.cleaned_data['marque']

        if nouveau_modele:
            modele, _ = Modele.objects.get_or_create(marque=marque, modele=nouveau_modele)
            form.instance.modele = modele

        return super().form_valid(form)
