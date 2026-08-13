from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.db.models import Q

from garages.mixins import GarageLectureMixin, GarageEcritureMixin
from garages.utils import get_garage_actif
from vehicules.models import Vehicule, Marque, Modele
from vehicules.forms import VehiculeForm, VenteForm


class ListVehiculeView(GarageLectureMixin, ListView):
    model = Vehicule
    template_name = 'vehicules/list_vehicules.html'
    context_object_name = 'vehicules'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related('marque', 'modele', 'garage')
        params = self.request.GET

        if params.get('garage', 'actif') == 'actif':
            garage_actif = get_garage_actif(self.request)
            qs = qs.filter(garage=garage_actif) if garage_actif else qs.none()

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

        transmissions = params.getlist('transmission')
        if transmissions:
            qs = qs.filter(transmission__in=transmissions)

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

        # Référence tous garages confondus (sans aucun filtre de la requête) :
        # sert uniquement aux badges de la section Garage, pour que chaque
        # option affiche son propre total indépendamment du garage
        # actuellement sélectionné.
        qs_tous_garages = GarageLectureMixin.get_queryset(self)
        garage_actif_courant = get_garage_actif(self.request)

        f_garage = params.get('garage', 'actif')
        if f_garage == 'actif':
            base_qs = qs_tous_garages.filter(garage=garage_actif_courant) if garage_actif_courant else qs_tous_garages.none()
        else:
            base_qs = qs_tous_garages

        # Compteurs "Statut" : reflètent le garage sélectionné, mais pas le
        # statut lui-même (sinon on ne pourrait plus voir combien de véhicules
        # sont vendus une fois qu'on filtre sur "En stock").
        ctx['count_total'] = base_qs.count()
        ctx['count_stock'] = base_qs.filter(date_vente__isnull=True).count()
        ctx['count_vendu'] = base_qs.filter(date_vente__isnull=False).count()

        f_statut = params.get('statut', 'tous')

        def appliquer_statut(qs):
            if f_statut == 'en-stock':
                return qs.filter(date_vente__isnull=True)
            elif f_statut == 'vendu':
                return qs.filter(date_vente__isnull=False)
            return qs

        # Compteurs "Garage" : reflètent le statut sélectionné, mais pas le
        # garage lui-même (chaque option affiche son propre total).
        qs_tous_garages_statut = appliquer_statut(qs_tous_garages)
        ctx['count_tous_garages'] = qs_tous_garages_statut.count()
        ctx['count_garage_actif'] = (
            qs_tous_garages_statut.filter(garage=garage_actif_courant).count() if garage_actif_courant else 0
        )

        # Marque / Énergie / Transmission : reflètent le garage et le statut
        # sélectionnés.
        base_qs_facettes = appliquer_statut(base_qs)

        ctx['marques'] = Marque.objects.filter(vehicule__in=base_qs_facettes).distinct().order_by('marque')

        ctx['energie_filters'] = [
            {
                'value': value,
                'label': label,
                'count': base_qs_facettes.filter(energie=value).count(),
            }
            for value, label in Vehicule.Energie.choices
        ]

        ctx['transmission_filters'] = [
            {
                'value': value,
                'label': label,
                'count': base_qs_facettes.filter(transmission=value).count(),
            }
            for value, label in Vehicule.Transmission.choices
        ]

        ctx['f_statut']        = f_statut
        ctx['f_energies']      = params.getlist('energie')
        ctx['f_marques']       = params.getlist('marque')
        ctx['f_transmissions'] = params.getlist('transmission')
        ctx['f_search']        = params.get('q', '')
        ctx['f_tri']           = params.get('tri', 'marque')
        ctx['f_garage']        = f_garage

        return ctx


class DetailVehiculeView(GarageLectureMixin, DetailView):
    model = Vehicule
    template_name = 'vehicules/detail_vehicule.html'
    context_object_name = 'vehicule'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['remises_en_etat'] = self.object.remises_en_etat.all()
        return context


class AjoutVehiculeView(GarageEcritureMixin, CreateView):
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
        form.instance.garage = self.get_garage_actif()

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


class VendreVehiculeView(GarageEcritureMixin, UpdateView):
    model = Vehicule
    form_class = VenteForm
    template_name = 'vehicules/vendre_vehicule.html'
    context_object_name = 'vehicule'

    def get_success_url(self):
        return reverse_lazy('vehicules:detail-vehicule', kwargs={'pk': self.object.pk})


class ModifierVehiculeView(GarageEcritureMixin, UpdateView):
    model = Vehicule
    form_class = VehiculeForm
    template_name = 'vehicules/modifier_vehicule.html'
    context_object_name = 'vehicule'

    def get_success_url(self):
        return reverse_lazy('vehicules:detail-vehicule', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['marques'] = Marque.objects.order_by('marque')
        context['modeles'] = Modele.objects.select_related('marque').order_by('marque__marque', 'modele')
        context['remises_en_etat'] = self.object.remises_en_etat.all()
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
