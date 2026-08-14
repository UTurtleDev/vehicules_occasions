from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from garages.models import Garage
from django.db.models import (
    Sum, F, Value, DecimalField, ExpressionWrapper, OuterRef, Subquery,
)
from django.db.models.functions import Coalesce
from django.utils import timezone
from datetime import datetime


def validateur_extensions(value):
    if not value.name.endswith('.pdf'):
        raise ValidationError('Le fichier doit être au format PDF.')
    
def validateur_prix(value):
    if value < 0:
        raise ValidationError('Le prix ne peut pas être négatif.')
    
def validateur_immatriculation(value):
    ...# TODO: Validateur plaque d'immatriculation

def validateur_annee(value):
    annee_encours = datetime.now().year
    if value < 1900 or value > annee_encours:
        raise ValidationError('Année invalide')


class VehiculeQuerySet(models.QuerySet):
    """
    Les coûts d'un véhicule existent en deux exemplaires.

    En propriétés Python (`prix_achat`, `marge_interne`…) : lisibles, mais
    calculées une instance à la fois. Parfait pour une fiche véhicule.

    Ici en annotations SQL : c'est la base de données qui fait la somme, en
    une seule requête, même sur tout le stock. Indispensable dès qu'on
    agrège (tableau de bord, tri par marge, filtre sur les ventes à perte).

    Les annotations portent le suffixe `_calc` parce que Django ne sait pas
    écraser une propriété du modèle : annoter `prix_achat` planterait.
    """

    def avec_couts(self):
        from remise_en_etat.models import RemiseEnEtat

        argent = DecimalField(max_digits=12, decimal_places=2)

        # Sous-requête et non Sum() sur la relation : un Sum() ferait une
        # jointure, qui dupliquerait la ligne du véhicule autant de fois
        # qu'il a de remises en état, et fausserait tous les autres totaux.
        frais = Coalesce(
            Subquery(
                RemiseEnEtat.objects
                .filter(vehicule=OuterRef('pk'))
                .values('vehicule')
                .annotate(total=Sum('montant'))
                .values('total')[:1],
                output_field=argent,
            ),
            Value(Decimal('0'), output_field=argent),
        )

        return self.annotate(
            frais_reel_calc=frais,
            prix_achat_calc=ExpressionWrapper(
                F('prix_vehicule') + F('prix_enchere') + F('prix_transport'),
                output_field=argent,
            ),
        ).annotate(
            cout_revient_calc=ExpressionWrapper(
                F('prix_achat_calc') + F('frais_reel_calc'), output_field=argent,
            ),
            # NULL tant que le véhicule n'est pas vendu : Sum() et Avg()
            # ignorent les NULL, les totaux ne comptent donc que les ventes.
            marge_fiscale_calc=ExpressionWrapper(
                F('prix_vente') - F('prix_achat_calc'), output_field=argent,
            ),
        ).annotate(
            marge_interne_calc=ExpressionWrapper(
                F('prix_vente') - F('cout_revient_calc'), output_field=argent,
            ),
        )

    def en_stock(self):
        return self.filter(date_vente__isnull=True)

    def vendus(self):
        return self.filter(date_vente__isnull=False)


class Vehicule(models.Model):
    # Choix
    class Transmission(models.TextChoices):
        MANUEL = 'manuel', 'Manuel'
        AUTOMATIQUE = 'automatique', 'Automatique'

    class Energie(models.TextChoices):
        ESSENCE = 'essence', 'Essence'
        DIESEL = 'diesel', 'Diesel'
        ELECTRIQUE = 'electrique', 'Electrique'
        HYBRIDE = 'hybride', 'Hybride'

    class CritAir(models.IntegerChoices):
        CRIT_AIR_0 = 0, 'Electrique'
        CRIT_AIR_1 = 1, '1'
        CRIT_AIR_2 = 2, '2'
        CRIT_AIR_3 = 3, '3'
        CRIT_AIR_4 = 4, '4'
        CRIT_AIR_5 = 5, '5'
        NON_CLASSE = 6, 'Non classé'


    # Gestion multi-garage
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='vehicules')

    # Acquisition
    date_achat = models.DateField()
    vendeur = models.CharField(max_length=100)
    facture_achat = models.FileField(upload_to='factures_achat/', validators=[validateur_extensions])
    prix_vehicule = models.DecimalField(max_digits=10, decimal_places=2, validators=[validateur_prix])
    prix_enchere = models.DecimalField(max_digits=10, decimal_places=2, validators=[validateur_prix])
    prix_transport = models.DecimalField(max_digits=10, decimal_places=2, validators=[validateur_prix])
    immatriculation = models.CharField(max_length=20, unique=True)
    vin = models.CharField(max_length=17, unique=True, blank=True, null=True)
    marque = models.ForeignKey('Marque', on_delete=models.CASCADE)
    modele = models.ForeignKey('Modele', on_delete=models.CASCADE)
    couleur = models.CharField(max_length=100)
    annee_vehicule = models.PositiveIntegerField(validators=[validateur_annee])
    crit_air = models.IntegerField(choices=CritAir.choices)
    kilometrage_achat = models.PositiveIntegerField(default=0)
    transmission = models.CharField(max_length=100, choices=Transmission.choices)
    energie = models.CharField(max_length=100, choices=Energie.choices)
    chevaux_dine = models.IntegerField()
    chevaux_fiscaux = models.IntegerField()

    # Vente
    date_vente = models.DateField(null=True, blank=True)
    numero_vente = models.IntegerField(null=True, blank=True)
    facture_vente = models.FileField(upload_to='factures_vente/', validators=[validateur_extensions], null=True, blank=True)
    acheteur = models.CharField(max_length=100, null=True, blank=True)
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2, validators=[validateur_prix], null=True, blank=True)
    kilometrage_vente = models.PositiveIntegerField(null=True, blank=True)

    objects = VehiculeQuerySet.as_manager()


    @property
    def prix_achat(self):
        return (self.prix_vehicule or 0) + (self.prix_enchere or 0) + (self.prix_transport or 0)

    @property
    def marge_fiscale(self):
        if self.prix_vente:
            return self.prix_vente - self.prix_achat
        else:
            return 0
        

    @property
    def frais_reel(self):
        return self.remises_en_etat.aggregate(Sum('montant'))['montant__sum'] or 0
    
    @property
    def cout_revient(self):
        return self.prix_achat + self.frais_reel


    @property
    def marge_interne(self):
        if self.prix_vente:
            return self.prix_vente - self.prix_achat - self.frais_reel
        else:
            return 0
        
    @property
    def vendu(self):
        return self.date_vente is not None

    @property
    def mois_en_stock(self):
        if self.vendu:
            return None
        jours = (timezone.now().date() - self.date_achat).days
        return int(jours // 30.4)

    @property
    def jours_detention(self):
        """
        Nombre de jours entre l'achat et la vente. Pour un véhicule encore
        en stock, l'âge du véhicule à ce jour. Contrairement à
        `mois_en_stock`, répond donc dans les deux cas : c'est ce qui permet
        de calculer un délai de rotation sur les véhicules vendus.
        """
        fin = self.date_vente or timezone.now().date()
        return (fin - self.date_achat).days

    def __str__(self):
        return f"{self.marque} {self.modele} - {self.immatriculation}"


class Marque(models.Model):
    marque = models.CharField(max_length=100)

    @property
    def nb_vehicules_marque(self):
        return Vehicule.objects.filter(marque=self).count()


    def __str__(self):
        
        return f"{self.marque}"
    
class Modele(models.Model):
    marque = models.ForeignKey(Marque, on_delete=models.CASCADE)
    modele = models.CharField(max_length=100)

    @property
    def nb_vehicules_modele(self):
        return Vehicule.objects.filter(modele=self).count()
    
    def __str__(self):
        return f"{self.modele}"
