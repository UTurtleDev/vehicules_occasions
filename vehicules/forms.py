from django import forms
from .models import Vehicule, Modele


class VehiculeForm(forms.ModelForm):
    nouvelle_marque = forms.CharField(required=False, label='Nouvelle marque')
    nouveau_modele = forms.CharField(required=False, label='Nouveau modèle')

    class Meta:
        model = Vehicule
        fields = [
            'marque', 'modele', 'annee_vehicule', 'couleur',
            'immatriculation', 'vin', 'energie', 'transmission',
            'crit_air', 'chevaux_dine', 'chevaux_fiscaux',
            'date_achat', 'vendeur', 'facture_achat',
            'prix_vehicule', 'prix_enchere', 'prix_transport',
            'kilometrage_achat',
        ]
        widgets = {
            'date_achat': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, garage=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['marque'].required = False
        self.fields['modele'].required = False
        self.fields['modele'].queryset = Modele.objects.select_related('marque').order_by('marque__marque', 'modele')

        # Le garage n'est pas un champ du formulaire : en création la vue ne
        # le pose sur l'instance qu'après validation. On l'injecte donc ici,
        # sinon impossible de savoir dans quel stock chercher un doublon.
        if garage is None and self.instance.garage_id:
            garage = self.instance.garage
        self.garage = garage

    def clean_immatriculation(self):
        return (self.cleaned_data.get('immatriculation') or '').strip().upper()

    def clean_vin(self):
        # null=True sur le modèle : le champ vide vaut None, pas ''.
        vin = self.cleaned_data.get('vin')
        return vin.strip().upper() if vin else vin

    def _doublon_en_stock(self, champ, valeur):
        """
        Un même véhicule peut revenir : acheté, vendu, puis repris au client
        qui rachète chez nous. Les deux passages sont deux fiches, donc deux
        cycles d'achat/vente et deux marges : c'est la lecture comptable
        juste, et ça interdit de fusionner les deux sur une seule fiche.

        L'unicité ne porte donc que sur le stock : deux véhicules NON vendus
        du même garage ne peuvent pas partager une plaque ou un VIN. Une
        fiche vendue, elle, ne bloque plus rien.

        Vérifié ici et pas par une contrainte de base : MySQL ne sait pas
        faire d'index unique conditionnel, Django l'ignorerait en silence en
        production tout en l'appliquant en SQLite au développement.
        """
        if not valeur or self.garage is None:
            return None
        doublons = Vehicule.objects.filter(
            garage=self.garage, date_vente__isnull=True, **{champ: valeur},
        )
        if self.instance.pk:
            doublons = doublons.exclude(pk=self.instance.pk)
        return doublons.first()

    def clean(self):
        cleaned_data = super().clean()
        marque = cleaned_data.get('marque')
        nouvelle_marque = cleaned_data.get('nouvelle_marque', '').strip()
        modele = cleaned_data.get('modele')
        nouveau_modele = cleaned_data.get('nouveau_modele', '').strip()

        if not marque and not nouvelle_marque:
            self.add_error('marque', 'Sélectionnez une marque ou saisissez-en une nouvelle.')

        if not modele and not nouveau_modele:
            self.add_error('modele', 'Sélectionnez un modèle ou saisissez-en un nouveau.')

        doublon = self._doublon_en_stock('immatriculation', cleaned_data.get('immatriculation'))
        if doublon:
            self.add_error('immatriculation', (
                f'Un véhicule encore en stock porte déjà cette immatriculation '
                f'({doublon.marque} {doublon.modele}, acquis le '
                f'{doublon.date_achat:%d/%m/%Y}).'
            ))

        doublon = self._doublon_en_stock('vin', cleaned_data.get('vin'))
        if doublon:
            self.add_error('vin', (
                f'Un véhicule encore en stock porte déjà ce VIN '
                f'({doublon.marque} {doublon.modele}, {doublon.immatriculation}).'
            ))

        return cleaned_data


class VenteForm(forms.ModelForm):
    class Meta:
        model = Vehicule
        fields = [
            'date_vente', 'acheteur', 'prix_vente', 'kilometrage_vente',
            'numero_vente', 'facture_vente',
        ]
        widgets = {
            'date_vente': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ('date_vente', 'acheteur', 'prix_vente', 'kilometrage_vente'):
            self.fields[name].required = True
