from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase
from django.urls import reverse

from garages.mixins import GarageEcritureMixin
from garages.models import Garage, GarageMembre
from garages.utils import GARAGE_SESSION_KEY
from vehicules.models import Marque, Modele, Vehicule

User = get_user_model()


def creer_garage(nom):
    return Garage.objects.create(
        nom=nom, adresse='1 rue Test', ville='Testville',
        code_postal='75000', telephone='0102030405', email='garage@test.fr',
    )


class GarageEcritureMixinTests(TestCase):
    def setUp(self):
        self.garage = creer_garage('Garage Test')
        self.gestionnaire = User.objects.create_user(email='gestionnaire@test.fr', password='x', first_name='G', last_name='G')
        self.lecteur = User.objects.create_user(email='lecteur@test.fr', password='x', first_name='L', last_name='L')
        self.etranger = User.objects.create_user(email='etranger@test.fr', password='x', first_name='E', last_name='E')
        GarageMembre.objects.create(user=self.gestionnaire, garage=self.garage, role=GarageMembre.Role.GESTIONNAIRE)
        GarageMembre.objects.create(user=self.lecteur, garage=self.garage, role=GarageMembre.Role.LECTURE)

    def _mixin_pour(self, user):
        request = RequestFactory().get('/')
        request.user = user
        session = self.client.session
        session[GARAGE_SESSION_KEY] = self.garage.id
        session.save()
        request.session = session
        mixin = GarageEcritureMixin()
        mixin.request = request
        return mixin

    def test_gestionnaire_a_le_garage_en_ecriture(self):
        mixin = self._mixin_pour(self.gestionnaire)
        self.assertEqual(mixin.get_garage_ecriture(), self.garage)

    def test_lecteur_n_a_pas_le_garage_en_ecriture(self):
        mixin = self._mixin_pour(self.lecteur)
        self.assertIsNone(mixin.get_garage_ecriture())

    def test_etranger_n_a_pas_le_garage_en_ecriture(self):
        mixin = self._mixin_pour(self.etranger)
        self.assertIsNone(mixin.get_garage_ecriture())

    def test_dispatch_refuse_le_lecteur(self):
        mixin = self._mixin_pour(self.lecteur)
        with self.assertRaises(PermissionDenied):
            mixin.dispatch(mixin.request)


class RolesSurLesVuesTests(TestCase):
    """
    Vérifie sur les vraies URL que le lecteur ne peut pas écrire, et que les
    boutons d'action ne lui sont pas proposés.
    """

    def setUp(self):
        self.garage = creer_garage('Garage 1')
        self.autre_garage = creer_garage('Garage 2')

        self.gestionnaire = User.objects.create_user(email='gestionnaire@test.fr', password='motdepasse', first_name='G', last_name='G')
        self.lecteur = User.objects.create_user(email='lecteur@test.fr', password='motdepasse', first_name='L', last_name='L')
        GarageMembre.objects.create(user=self.gestionnaire, garage=self.garage, role=GarageMembre.Role.GESTIONNAIRE)
        GarageMembre.objects.create(user=self.lecteur, garage=self.garage, role=GarageMembre.Role.LECTURE)

        marque = Marque.objects.create(marque='Renault')
        modele = Modele.objects.create(marque=marque, modele='Clio')
        self.vehicule = Vehicule.objects.create(
            garage=self.garage, date_achat=date(2025, 1, 10), vendeur='Enchères',
            prix_vehicule=5000, prix_enchere=200, prix_transport=300,
            immatriculation='AA-123-BB', marque=marque, modele=modele,
            couleur='Bleu', annee_vehicule=2018, crit_air=1,
            kilometrage_achat=90000, transmission=Vehicule.Transmission.MANUEL,
            energie=Vehicule.Energie.ESSENCE, chevaux_dine=90, chevaux_fiscaux=5,
        )

    def _connecter(self, user):
        self.client.force_login(user)
        session = self.client.session
        session[GARAGE_SESSION_KEY] = self.garage.id
        session.save()

    def test_lecteur_ne_peut_pas_ouvrir_le_formulaire_de_vente(self):
        self._connecter(self.lecteur)
        reponse = self.client.get(reverse('vehicules:vendre-vehicule', args=[self.vehicule.pk]))
        self.assertEqual(reponse.status_code, 403)

    def test_lecteur_ne_peut_pas_enregistrer_une_vente(self):
        self._connecter(self.lecteur)
        reponse = self.client.post(reverse('vehicules:vendre-vehicule', args=[self.vehicule.pk]), {
            'date_vente': '2025-06-01', 'acheteur': 'Client', 'prix_vente': '8000',
            'kilometrage_vente': '95000',
        })
        self.assertEqual(reponse.status_code, 403)
        self.vehicule.refresh_from_db()
        self.assertIsNone(self.vehicule.date_vente)

    def test_lecteur_ne_peut_pas_ajouter_de_frais(self):
        self._connecter(self.lecteur)
        reponse = self.client.get(reverse('remise_en_etat:ajouter-remise', args=[self.vehicule.pk]))
        self.assertEqual(reponse.status_code, 403)

    def test_lecteur_ne_peut_pas_modifier_le_vehicule(self):
        self._connecter(self.lecteur)
        reponse = self.client.get(reverse('vehicules:modifier-vehicule', args=[self.vehicule.pk]))
        self.assertEqual(reponse.status_code, 403)

    def test_lecteur_voit_la_fiche_sans_bouton_d_action(self):
        self._connecter(self.lecteur)
        reponse = self.client.get(reverse('vehicules:detail-vehicule', args=[self.vehicule.pk]))
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, reverse('vehicules:vendre-vehicule', args=[self.vehicule.pk]))
        self.assertNotContains(reponse, reverse('vehicules:modifier-vehicule', args=[self.vehicule.pk]))
        self.assertContains(reponse, 'Lecture seule sur ce garage')

    def test_lecteur_ne_voit_pas_le_bouton_ajouter_un_frais(self):
        self._connecter(self.lecteur)
        reponse = self.client.get(reverse('remise_en_etat:liste-remises', args=[self.vehicule.pk]))
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, reverse('remise_en_etat:ajouter-remise', args=[self.vehicule.pk]))

    def test_lecteur_ne_voit_pas_le_bouton_ajouter_un_vehicule(self):
        self._connecter(self.lecteur)
        reponse = self.client.get(reverse('vehicules:garages'))
        self.assertEqual(reponse.status_code, 200)
        self.assertNotContains(reponse, reverse('vehicules:ajouter-vehicule'))

    def test_gestionnaire_enregistre_la_vente(self):
        self._connecter(self.gestionnaire)
        reponse = self.client.post(reverse('vehicules:vendre-vehicule', args=[self.vehicule.pk]), {
            'date_vente': '2025-06-01', 'acheteur': 'Client', 'prix_vente': '8000',
            'kilometrage_vente': '95000',
        })
        self.assertRedirects(reponse, reverse('vehicules:detail-vehicule', args=[self.vehicule.pk]))
        self.vehicule.refresh_from_db()
        self.assertEqual(self.vehicule.date_vente, date(2025, 6, 1))
        self.assertEqual(self.vehicule.prix_vente, 8000)

    def test_gestionnaire_voit_les_boutons_d_action(self):
        self._connecter(self.gestionnaire)
        reponse = self.client.get(reverse('vehicules:detail-vehicule', args=[self.vehicule.pk]))
        self.assertContains(reponse, reverse('vehicules:vendre-vehicule', args=[self.vehicule.pk]))
        self.assertContains(reponse, reverse('vehicules:modifier-vehicule', args=[self.vehicule.pk]))

    def test_gestionnaire_ne_peut_pas_ecrire_sur_un_autre_garage(self):
        """Le garage actif borne l'écriture, même pour un gestionnaire."""
        GarageMembre.objects.create(user=self.gestionnaire, garage=self.autre_garage, role=GarageMembre.Role.GESTIONNAIRE)
        self.client.force_login(self.gestionnaire)
        session = self.client.session
        session[GARAGE_SESSION_KEY] = self.autre_garage.id
        session.save()
        reponse = self.client.get(reverse('vehicules:vendre-vehicule', args=[self.vehicule.pk]))
        self.assertEqual(reponse.status_code, 404)
