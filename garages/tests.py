from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase

from garages.mixins import GarageEcritureMixin
from garages.models import Garage, GarageMembre
from garages.utils import GARAGE_SESSION_KEY

User = get_user_model()


class GarageEcritureMixinTests(TestCase):
    def setUp(self):
        self.garage = Garage.objects.create(
            nom='Garage Test', adresse='1 rue Test', ville='Testville',
            code_postal='75000', telephone='0102030405', email='garage@test.fr',
        )
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
