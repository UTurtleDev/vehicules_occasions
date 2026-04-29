from django import forms
from django.forms import inlineformset_factory

from .models import Garage
from users.models import User


GarageImageFormSet = inlineformset_factory(User, Garage)
...
