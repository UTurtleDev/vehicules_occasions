from django.urls import path

from . import views

app_name = 'users'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('connexion/', views.login_modal, name='login_modal'),
    path('connexion/soumettre/', views.login_submit, name='login_submit'),
    path('connexion/fermer/', views.modal_close, name='modal_close'),
    path('deconnexion/', views.logout_view, name='logout'),
]

