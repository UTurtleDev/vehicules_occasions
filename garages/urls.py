from django.urls import path
from .views import garages


app_name = 'garages'

urlpatterns = [
    path('', garages, name='garages'),
]