from django.db import models
from django.core.exceptions import ValidationError
from garages.models import Garage


def validateur_extensions(value):
    if not value.name.endswith('.pdf'):
        raise ValidationError('Le fichier doit être au format PDF.')
    
def validateur_prix(value):
    if value < 0:
        raise ValidationError('Le prix ne peut pas être négatif.')
    
def validateur_immatriculation(value):
    ...

def validateur_annee(value):
    if value < 1900 or value > 2100:
        raise ValidationError('Année invalide')


class Vehicule(models.Model):
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
    marque = models.CharField(max_length=100)
    modele = models.CharField(max_length=100)
    couleur = models.CharField(max_length=100)
    annee_vehicule = models.PositiveIntegerField(validators=[validateur_annee])
    transmission = models.CharField(max_length=100)
    energie = models.CharField(max_length=100)
    chevaux_dine = models.IntegerField()
    chevaux_fiscaux = models.IntegerField()

    # Vente
    date_vente = models.DateField(null=True, blank=True)
    numero_vente = models.IntegerField(null=True, blank=True)
    facture_vente = models.FileField(upload_to='factures_vente/', validators=[validateur_extensions], null=True, blank=True)
    acheteur = models.CharField(max_length=100, null=True, blank=True)
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2, validators=[validateur_prix], null=True, blank=True)

    @property
    def prix_achat(self):
        return self.prix_vehicule + self.prix_enchere + self.prix_transport

    @property
    def marge(self):
        return self.prix_vente - self.prix_achat
    
    def __str__(self):
        if self.prix_vente:
            return f"{self.marque} {self.modele} ({self.immatriculation}) - {self.marge} €"
        else:
            return f"{self.marque} {self.modele} ({self.immatriculation}) - (-) €"


