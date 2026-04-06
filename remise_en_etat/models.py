from django.db import models

from vehicules.models import Vehicule, validateur_prix


class RemiseEnEtat(models.Model):

    class Type_ree(models.TextChoices):
        CT = 'ct', 'Contrôle technique'
        PIECES = 'pieces', 'Pièces'
        MO = 'mo', 'Main d\'oeuvre'

    vehicule = models.ForeignKey(Vehicule, on_delete=models.CASCADE, related_name='remises_en_etat')
    type_ree = models.CharField(max_length=100, choices=Type_ree.choices, blank=True, null=True, verbose_name="Type entretien")
    description = models.TextField(max_length=1000, blank=True, null=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2, validators=[validateur_prix], blank=True, null=True)

    def __str__(self):
        return f"{self.vehicule} - {self.type_ree} - {self.montant} €"