from django.db import models
from django.core.exceptions import ValidationError
from garages.models import Garage
from django.db.models import Sum


def validateur_extensions(value):
    if not value.name.endswith('.pdf'):
        raise ValidationError('Le fichier doit être au format PDF.')
    
def validateur_prix(value):
    if value < 0:
        raise ValidationError('Le prix ne peut pas être négatif.')
    
def validateur_immatriculation(value):
    ...# TODO: Validateur plaque d'immatriculation

def validateur_annee(value):
    if value < 1900 or value > 2100: #TODO: l'année ne peut etre supérieur a l'année actuelle
        raise ValidationError('Année invalide')


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


    # Gestion multi-garage
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE)

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
    crit_air = models.IntegerField()
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
    def marge_interne(self):
        if self.prix_vente:
            return self.prix_vente - self.prix_achat - self.frais_reel
        else:
            return 0
        
    @property
    def vendu(self):
        return self.date_vente is not None
    
    def __str__(self):
        return f"{self.marque} {self.modele} - {self.immatriculation}"


class Marque(models.Model):
    marque = models.CharField(max_length=100)

    def __str__(self):
        
        return f"{self.marque}"
    
class Modele(models.Model):
    marque = models.ForeignKey(Marque, on_delete=models.CASCADE)
    modele = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.modele}"
