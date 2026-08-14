from decimal import Decimal

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from abonnements.models import Abonnement
from django.utils import timezone
from datetime import timedelta    


def validateur_code_postal(value):
    if len(value) != 5:
        raise ValidationError('Le code postal doit avoir 5 chiffres.')

def validateur_telephone(value):
    if len(value) != 10:
        raise ValidationError('Le numéro de téléphone doit avoir 10 chiffres.')
    

def validateur_compte(value):
    if not value.isdigit():
        raise ValidationError('Un compte comptable ne contient que des chiffres.')


class Garage(models.Model):
    membres = models.ManyToManyField(settings.AUTH_USER_MODEL, through='GarageMembre', related_name='garages')
    nom = models.CharField(max_length=100)
    adresse = models.CharField(max_length=200)
    ville = models.CharField(max_length=100)
    code_postal= models.CharField(max_length=5, validators=[validateur_code_postal])
    telephone = models.CharField(max_length=10, validators=[validateur_telephone])
    email = models.EmailField()
    abonnement = models.ForeignKey(Abonnement, on_delete=models.SET_NULL, null=True)
    date_debut_essai = models.DateField(null=True, blank=True)

    @property
    def essai_actif(self):
        if self.date_debut_essai is None:
            return False
        return (timezone.now().date() - self.date_debut_essai) < timedelta(days=30)
    
    def __str__(self):
        return self.nom


class GarageMembre(models.Model):
    """Rôle d'un utilisateur sur un garage : gestionnaire (lecture + écriture) ou lecture seule."""

    class Role(models.TextChoices):
        GESTIONNAIRE = 'gestionnaire', 'Gestionnaire'
        LECTURE = 'lecture', 'Lecture'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='garage_memberships')
    garage = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='memberships')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GESTIONNAIRE)

    class Meta:
        unique_together = ('user', 'garage')

    def __str__(self):
        return f"{self.user} · {self.garage} ({self.get_role_display()})"


class ParametrageComptable(models.Model):
    """
    Comptes et taux de TVA utilisés par l'export comptable d'un garage.

    Les véhicules d'occasion relèvent du régime de la TVA sur la marge :
    l'écriture ne porte pas sur le prix de vente, mais sur la seule marge,
    ventilée entre son montant HT et sa TVA. D'où exactement trois comptes.

    Le taux vit ici, à côté des comptes, pour qu'un changement de taux se
    règle au même endroit qu'un changement de plan comptable.
    """

    garage = models.OneToOneField(
        Garage, on_delete=models.CASCADE, related_name='parametrage_comptable',
    )
    compte_ventes_totales = models.CharField(
        max_length=20, default='707000000', validators=[validateur_compte],
        verbose_name='Ventes totale',
        help_text='Compte débité du montant TTC de la marge.',
    )
    compte_ventes_prix_achat = models.CharField(
        max_length=20, default='707010000', validators=[validateur_compte],
        verbose_name="Ventes au prix d'achat HT",
        help_text='Compte crédité du montant HT de la marge.',
    )
    compte_tva_collectee = models.CharField(
        max_length=20, default='445710090', validators=[validateur_compte],
        verbose_name='TVA collectée',
        help_text='Compte crédité de la TVA calculée sur la marge.',
    )
    taux_tva = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('20.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        verbose_name='Taux de TVA (%)',
    )

    class Meta:
        verbose_name = 'paramétrage comptable'
        verbose_name_plural = 'paramétrages comptables'

    @classmethod
    def pour(cls, garage):
        """
        Paramétrage du garage, ou une instance non sauvegardée portant les
        valeurs par défaut.

        Renvoyer un objet en mémoire plutôt qu'un get_or_create évite deux
        ennuis : écrire en base sur une simple requête GET d'export, et
        devoir migrer les données des garages déjà créés.
        """
        return cls.objects.filter(garage=garage).first() or cls(garage=garage)

    def __str__(self):
        return f"Paramétrage comptable · {self.garage}"
