from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from abonnements.models import Abonnement


def validateur_code_postal(value):
    if len(value) != 5:
        raise ValidationError('Le code postal doit avoir 5 chiffres.')

def validateur_telephone(value):
    if len(value) != 10:
        raise ValidationError('Le numéro de téléphone doit avoir 10 chiffres.')
    

class Garage(models.Model):
    proprietaire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='garages')
    nom = models.CharField(max_length=100)
    adresse = models.CharField(max_length=200)
    ville = models.CharField(max_length=100)
    code_postal= models.CharField(max_length=5, validators=[validateur_code_postal])
    telephone = models.CharField(max_length=10, validators=[validateur_telephone])
    email = models.EmailField()
    abonnement = models.ForeignKey(Abonnement, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.nom} - {self.abonnement}"
