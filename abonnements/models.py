from django.db import models

class Abonnement(models.Model):

    class Duree(models.IntegerChoices):
        # Premier argument est le code, deuxieme est l'affichage
        MENSUEL = 30, 'Mensuel'
        ANNUEL = 365, 'Annuel'

    class Plan(models.TextChoices):
        # Premier argument est le code, deuxieme est l'affichage
        FREE = 'free', 'Free'
        PRO = 'pro', 'Pro'
        ENTREPRISE = 'entreprise', 'Entreprise'

    plan = models.CharField(max_length=100, choices=Plan.choices, default=Plan.FREE)
    prix = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    duree = models.IntegerField(choices=Duree.choices, default=Duree.MENSUEL)
    description = models.TextField(blank=True)

    def __str__(self):
        # get display : méthode générée automatique par Django pour les champs de choix, pour afficher l'affichage et non le code
        return self.get_plan_display()
