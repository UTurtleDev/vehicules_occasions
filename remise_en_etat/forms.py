from django import forms
from .models import RemiseEnEtat


class RemiseEnEtatForm(forms.ModelForm):
    class Meta:
        model = RemiseEnEtat
        fields = ['type_ree', 'description', 'montant']
