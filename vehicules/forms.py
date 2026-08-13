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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['marque'].required = False
        self.fields['modele'].required = False
        self.fields['modele'].queryset = Modele.objects.select_related('marque').order_by('marque__marque', 'modele')

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
