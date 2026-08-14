from django import forms

from .models import ParametrageComptable


class ParametrageComptableForm(forms.ModelForm):
    class Meta:
        model = ParametrageComptable
        fields = [
            'compte_ventes_totales',
            'compte_ventes_prix_achat',
            'compte_tva_collectee',
            'taux_tva',
        ]
        widgets = {
            'compte_ventes_totales': forms.TextInput(attrs={'inputmode': 'numeric'}),
            'compte_ventes_prix_achat': forms.TextInput(attrs={'inputmode': 'numeric'}),
            'compte_tva_collectee': forms.TextInput(attrs={'inputmode': 'numeric'}),
            'taux_tva': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
        }
