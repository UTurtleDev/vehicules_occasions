from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.text import slugify
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, View
from django.db.models import Q, Count, Sum
from django.utils import timezone

from garages.mixins import GarageLectureMixin, GarageEcritureMixin
from garages.models import ParametrageComptable
from garages.utils import get_garage_actif
from vehicules.models import Vehicule, Marque, Modele
from vehicules.forms import VehiculeForm, VenteForm
from vehicules.exports import (
    PERIODES_EXPORT, PERIODE_DEFAUT, ecrire_csv, libelle_periode,
    lignes_ecritures, stock_a_la_date, suffixe_fichier, synthese,
    ventes_ecartees,
)
from vehicules.pdf import rendre_stock_pdf, rendre_synthese_pdf
from vehicules.utils import (
    PERIODES, bornes_periode, date_ou_none, moyenne_entiere, pourcentage,
)


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


# ═══════════════════ TABLEAU DE BORD ═══════════════════

SEUIL_DORMANT_JOURS = 90


class TableauDeBordView(GarageLectureMixin, TemplateView):
    """
    Deux lectures indépendantes du même stock.

    « Stock » est une photo à l'instant T : ce que le garage détient
    aujourd'hui, et le capital que ça immobilise. La période ne s'y applique
    pas, filtrer le stock actuel sur « mois en cours » n'aurait pas de sens.

    « Activité » couvre les véhicules vendus pendant la période, bornés sur
    la date de vente.

    Les filtres marque / énergie / transmission, eux, s'appliquent aux deux.
    """

    template_name = 'vehicules/tableau_de_bord.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET
        aujourdhui = timezone.now().date()

        # ── Périmètre : quel garage ──────────────────────────────────
        tous_garages = self.get_queryset()
        garage_actif = get_garage_actif(self.request)
        f_garage = params.get('garage', 'actif')

        if f_garage == 'actif':
            perimetre = tous_garages.filter(garage=garage_actif) if garage_actif else tous_garages.none()
        else:
            perimetre = tous_garages

        # ── Filtres portant sur le véhicule lui-même ─────────────────
        # Les pk de marque viennent de l'URL : on ne garde que des entiers,
        # sinon un ?marque=abc ferait remonter une ValueError.
        f_marques = [v for v in params.getlist('marque') if v.isdigit()]
        f_energies = params.getlist('energie')
        f_transmissions = params.getlist('transmission')

        qs = perimetre
        if f_marques:
            qs = qs.filter(marque__pk__in=f_marques)
        if f_energies:
            qs = qs.filter(energie__in=f_energies)
        if f_transmissions:
            qs = qs.filter(transmission__in=f_transmissions)

        # ── Période, appliquée à la seule activité ───────────────────
        f_periode = params.get('periode', '12mois')
        if f_periode == 'perso':
            debut, fin = date_ou_none(params.get('du')), date_ou_none(params.get('au'))
        else:
            if f_periode not in dict(PERIODES):
                f_periode = '12mois'
            debut, fin = bornes_periode(f_periode, aujourdhui)

        chiffre = qs.avec_couts()

        # ══════════════ BLOC STOCK ══════════════
        stock = chiffre.en_stock()
        stock_agg = stock.aggregate(nb=Count('pk'), valeur=Sum('cout_revient_calc'))

        ages = [(aujourdhui - achat).days
                for achat in qs.en_stock().values_list('date_achat', flat=True)]

        dormants = stock.filter(
            date_achat__lte=aujourdhui - timedelta(days=SEUIL_DORMANT_JOURS)
        ).order_by('date_achat')
        dormants_agg = dormants.aggregate(nb=Count('pk'), capital=Sum('cout_revient_calc'))

        ctx['stock'] = {
            'nb': stock_agg['nb'],
            'valeur': stock_agg['valeur'] or 0,
            'age_moyen': moyenne_entiere(ages),
            'nb_dormant': dormants_agg['nb'],
            'capital_dormant': dormants_agg['capital'] or 0,
        }

        # ══════════════ BLOC ACTIVITÉ ══════════════
        vendus = chiffre.vendus()
        if debut:
            vendus = vendus.filter(date_vente__gte=debut)
        if fin:
            vendus = vendus.filter(date_vente__lte=fin)

        activite = vendus.aggregate(
            nb=Count('pk'),
            ca=Sum('prix_vente'),
            marge=Sum('marge_interne_calc'),
            marge_fiscale=Sum('marge_fiscale_calc'),
            frais=Sum('frais_reel_calc'),
        )
        nb_vendus = activite['nb']
        ca = activite['ca'] or 0
        marge = activite['marge'] or 0
        frais = activite['frais'] or 0

        rotations = [(vente - achat).days
                     for achat, vente in vendus.values_list('date_achat', 'date_vente')]

        ctx['activite'] = {
            'nb': nb_vendus,
            'ca': ca,
            'marge': marge,
            'marge_fiscale': activite['marge_fiscale'] or 0,
            'marge_moyenne': marge / nb_vendus if nb_vendus else None,
            'taux_marge': pourcentage(marge, ca),
            'rotation': moyenne_entiere(rotations),
            'frais_moyens': frais / nb_vendus if nb_vendus else None,
        }

        # ══════════════ TABLES ══════════════
        details = ('marque', 'modele', 'garage')
        ctx['meilleures_marges'] = vendus.select_related(*details).order_by('-marge_interne_calc')[:5]
        ctx['pires_marges'] = vendus.select_related(*details).order_by('marge_interne_calc')[:5]
        ctx['nb_ventes_a_perte'] = vendus.filter(marge_interne_calc__lt=0).count()
        ctx['dormants'] = dormants.select_related(*details).order_by('date_achat')[:10]

        # ══════════════ FACETTES DE LA SIDEBAR ══════════════
        # Comptées sur le périmètre garage, sans les filtres véhicule : chaque
        # option affiche donc son propre total, et ne tombe jamais à zéro
        # juste parce qu'une autre option est cochée.
        def compter(champ):
            return dict(perimetre.values(champ).annotate(n=Count('pk')).values_list(champ, 'n'))

        compte_marques = compter('marque')
        ctx['marque_filters'] = [
            {'value': m.pk, 'label': m.marque, 'count': compte_marques[m.pk]}
            for m in Marque.objects.filter(pk__in=compte_marques).order_by('marque')
        ]

        compte_energies = compter('energie')
        ctx['energie_filters'] = [
            {'value': v, 'label': label, 'count': compte_energies.get(v, 0)}
            for v, label in Vehicule.Energie.choices
        ]

        compte_transmissions = compter('transmission')
        ctx['transmission_filters'] = [
            {'value': v, 'label': label, 'count': compte_transmissions.get(v, 0)}
            for v, label in Vehicule.Transmission.choices
        ]

        ctx['count_tous_garages'] = tous_garages.count()
        ctx['count_garage_actif'] = tous_garages.filter(garage=garage_actif).count() if garage_actif else 0

        # ══════════════ ÉTAT DES FILTRES ══════════════
        ctx['periodes'] = PERIODES
        ctx['f_periode'] = f_periode
        ctx['f_garage'] = f_garage
        ctx['f_marques'] = f_marques
        ctx['f_energies'] = f_energies
        ctx['f_transmissions'] = f_transmissions
        ctx['f_du'] = params.get('du', '')
        ctx['f_au'] = params.get('au', '')
        ctx['periode_debut'] = debut
        ctx['periode_fin'] = fin
        ctx['seuil_dormant'] = SEUIL_DORMANT_JOURS
        ctx['filtres_actifs'] = bool(
            f_marques or f_energies or f_transmissions
            or f_garage != 'actif' or f_periode != '12mois'
        )

        return ctx


# ═══════════════════ EXPORTS ═══════════════════

class ExportMixin(GarageLectureMixin):
    """
    Socle des trois vues d'export : même période, même périmètre.

    Le périmètre est le garage actif seul, et non tous les garages de
    l'utilisateur comme sur le tableau de bord. Un export part chez un
    dirigeant ou chez un comptable : mélanger les écritures de deux garages
    dans un même fichier n'aurait aucun sens.
    """

    def resoudre_periode(self):
        params = self.request.GET
        aujourdhui = timezone.now().date()
        code = params.get('periode', PERIODE_DEFAUT)

        if code == 'perso':
            debut, fin = date_ou_none(params.get('du')), date_ou_none(params.get('au'))
        else:
            if code not in dict(PERIODES_EXPORT):
                code = PERIODE_DEFAUT
            debut, fin = bornes_periode(code, aujourdhui)

        return code, debut, fin, aujourdhui

    def resoudre_date_stock(self):
        """
        Date de la photo de stock, indépendante de la période.

        L'état du stock répond à « que détenais-je ce jour-là », une
        question à une seule date : la borner sur une période n'aurait pas
        de sens. Par défaut, aujourd'hui.
        """
        aujourdhui = timezone.now().date()
        return date_ou_none(self.request.GET.get('stock_au')) or aujourdhui

    def get_perimetre(self):
        garage = get_garage_actif(self.request)
        qs = self.get_queryset()
        qs = qs.filter(garage=garage) if garage else qs.none()
        return qs.avec_couts()

    def donnees_export(self):
        """(garage, code, données de la synthèse, bornes) — le tronc commun."""
        code, debut, fin, aujourdhui = self.resoudre_periode()
        donnees = synthese(self.get_perimetre(), debut, fin, aujourdhui)
        return {
            'garage': get_garage_actif(self.request),
            'code': code,
            'debut': debut,
            'fin': fin,
            'aujourdhui': aujourdhui,
            'donnees': donnees,
            'libelle': libelle_periode(code, debut, fin),
        }

    def nom_fichier(self, base, extension, suffixe=None):
        garage = get_garage_actif(self.request)
        morceaux = [base]
        # Le nom du garage n'est utile que s'il y en a plusieurs à distinguer.
        if garage and self.request.user.garages.count() > 1:
            morceaux.append(slugify(garage.nom))
        if suffixe is None:
            _, debut, fin, aujourdhui = self.resoudre_periode()
            suffixe = suffixe_fichier(debut, fin, aujourdhui)
        morceaux.append(suffixe)
        return f"{'-'.join(morceaux)}.{extension}"


class ExportsView(ExportMixin, TemplateView):
    """Choix de la période, aperçu des chiffres, et les deux téléchargements."""

    template_name = 'vehicules/exports.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        contexte = self.donnees_export()
        params = self.request.GET

        ctx.update(contexte)
        ctx['periodes'] = PERIODES_EXPORT
        ctx['f_periode'] = contexte['code']
        ctx['f_du'] = params.get('du', '')
        ctx['f_au'] = params.get('au', '')
        ctx['parametrage'] = ParametrageComptable.pour(contexte['garage'])
        # Signalées explicitement : ces ventes sortent dans le PDF mais pas
        # dans le CSV, et une disparition silencieuse serait un piège.
        ctx['ecartees'] = ventes_ecartees(contexte['donnees']['ventes'])

        stock_au = self.resoudre_date_stock()
        ctx['stock_au'] = stock_au
        ctx['f_stock_au'] = params.get('stock_au', stock_au.isoformat())
        ctx['stock'] = stock_a_la_date(self.get_perimetre(), stock_au)
        return ctx


class ExportSynthesePdfView(ExportMixin, View):
    def get(self, request, *args, **kwargs):
        contexte = self.donnees_export()
        pdf = rendre_synthese_pdf(
            contexte['garage'], contexte['libelle'],
            contexte['donnees'], contexte['aujourdhui'],
        )
        reponse = HttpResponse(pdf, content_type='application/pdf')
        nom = self.nom_fichier('synthese-ventes', 'pdf')
        reponse['Content-Disposition'] = f'attachment; filename="{nom}"'
        return reponse


class ExportStockPdfView(ExportMixin, View):
    def get(self, request, *args, **kwargs):
        a_la_date = self.resoudre_date_stock()
        donnees = stock_a_la_date(self.get_perimetre(), a_la_date)
        pdf = rendre_stock_pdf(
            get_garage_actif(request), a_la_date, donnees, timezone.now().date(),
        )
        reponse = HttpResponse(pdf, content_type='application/pdf')
        nom = self.nom_fichier('etat-stock', 'pdf', suffixe=a_la_date.isoformat())
        reponse['Content-Disposition'] = f'attachment; filename="{nom}"'
        return reponse


class ExportComptableCsvView(ExportMixin, View):
    def get(self, request, *args, **kwargs):
        contexte = self.donnees_export()
        parametrage = ParametrageComptable.pour(contexte['garage'])
        contenu = ecrire_csv(
            lignes_ecritures(contexte['donnees']['ventes'], parametrage)
        )
        reponse = HttpResponse(contenu, content_type='text/csv; charset=utf-8')
        nom = self.nom_fichier('ecritures', 'csv')
        reponse['Content-Disposition'] = f'attachment; filename="{nom}"'
        return reponse
