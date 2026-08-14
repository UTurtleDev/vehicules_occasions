from django.urls import path

from . import views

app_name = 'garages'

urlpatterns = [
    path('changer/', views.changer_garage, name='changer-garage'),
    path(
        'parametrage-comptable/',
        views.ParametrageComptableView.as_view(),
        name='parametrage-comptable',
    ),
]
