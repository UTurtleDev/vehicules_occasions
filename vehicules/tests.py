from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from garages.models import Garage, GarageMembre, ParametrageComptable
from garages.utils import GARAGE_SESSION_KEY
from remise_en_etat.models import RemiseEnEtat
from vehicules.exports import (
    ecrire_csv, lignes_ecritures, stock_a_la_date, synthese, ventes_ecartees,
)
from vehicules.models import Marque, Modele, Vehicule
from vehicules.utils import bornes_periode

User = get_user_model()


def creer_garage(nom):
    return Garage.objects.create(
        nom=nom, adresse='1 rue Test', ville='Testville',
        code_postal='75000', telephone='0102030405', email='garage@test.fr',
    )


class BaseVehiculeTests(TestCase):
    """Un garage, un gestionnaire, une marque et un modèle prêts à l'emploi."""

    def setUp(self):
        self.garage = creer_garage('Garage Test')
        self.user = User.objects.create_user(
            email='gestionnaire@test.fr', password='x', first_name='G', last_name='G',
        )
        GarageMembre.objects.create(
            user=self.user, garage=self.garage, role=GarageMembre.Role.GESTIONNAIRE,
        )
        self.marque = Marque.objects.create(marque='Renault')
        self.modele = Modele.objects.create(marque=self.marque, modele='Clio')
        self.compteur_immat = 0

    def creer_vehicule(self, garage=None, prix_vehicule='10000', prix_enchere='500',
                       prix_transport='300', date_achat=None, **extra):
        self.compteur_immat += 1
        return Vehicule.objects.create(
            garage=garage or self.garage,
            date_achat=date_achat or date(2025, 1, 10),
            vendeur='Vendeur',
            facture_achat='factures_achat/test.pdf',
            prix_vehicule=Decimal(prix_vehicule),
            prix_enchere=Decimal(prix_enchere),
            prix_transport=Decimal(prix_transport),
            immatriculation=f'AA-{self.compteur_immat:03d}-AA',
            marque=self.marque,
            modele=self.modele,
            couleur='Gris',
            annee_vehicule=2020,
            crit_air=Vehicule.CritAir.CRIT_AIR_1,
            kilometrage_achat=50000,
            transmission=Vehicule.Transmission.MANUEL,
            energie=Vehicule.Energie.ESSENCE,
            chevaux_dine=100,
            chevaux_fiscaux=5,
            **extra,
        )


class AvecCoutsTests(BaseVehiculeTests):
    """Les annotations SQL doivent donner exactement le même résultat que les propriétés Python."""

    def test_annotations_egalent_les_proprietes(self):
        vehicule = self.creer_vehicule(
            date_vente=date(2025, 4, 10), prix_vente=Decimal('14000'),
        )
        RemiseEnEtat.objects.create(vehicule=vehicule, montant=Decimal('400'))

        annote = Vehicule.objects.avec_couts().get(pk=vehicule.pk)
        self.assertEqual(annote.prix_achat_calc, vehicule.prix_achat)
        self.assertEqual(annote.frais_reel_calc, vehicule.frais_reel)
        self.assertEqual(annote.cout_revient_calc, vehicule.cout_revient)
        self.assertEqual(annote.marge_fiscale_calc, vehicule.marge_fiscale)
        self.assertEqual(annote.marge_interne_calc, vehicule.marge_interne)

    def test_plusieurs_remises_ne_dupliquent_pas_le_vehicule(self):
        """Le piège du Sum() sur une relation : trois remises ne doivent pas tripler le prix d'achat."""
        vehicule = self.creer_vehicule()
        for montant in ('100', '200', '300'):
            RemiseEnEtat.objects.create(vehicule=vehicule, montant=Decimal(montant))

        annotes = Vehicule.objects.avec_couts()
        self.assertEqual(annotes.count(), 1)

        annote = annotes.get()
        self.assertEqual(annote.frais_reel_calc, Decimal('600'))
        self.assertEqual(annote.prix_achat_calc, Decimal('10800'))
        self.assertEqual(annote.cout_revient_calc, Decimal('11400'))

    def test_vehicule_sans_remise_a_des_frais_nuls(self):
        self.creer_vehicule()
        annote = Vehicule.objects.avec_couts().get()
        self.assertEqual(annote.frais_reel_calc, Decimal('0'))
        self.assertEqual(annote.cout_revient_calc, annote.prix_achat_calc)

    def test_marges_nulles_tant_que_le_vehicule_n_est_pas_vendu(self):
        self.creer_vehicule()
        annote = Vehicule.objects.avec_couts().get()
        self.assertIsNone(annote.marge_fiscale_calc)
        self.assertIsNone(annote.marge_interne_calc)


class JoursDetentionTests(BaseVehiculeTests):
    def test_vehicule_vendu_compte_de_l_achat_a_la_vente(self):
        vehicule = self.creer_vehicule(
            date_achat=date(2025, 1, 1), date_vente=date(2025, 3, 2), prix_vente=Decimal('12000'),
        )
        self.assertEqual(vehicule.jours_detention, 60)

    def test_vehicule_en_stock_compte_jusqu_a_aujourd_hui(self):
        achat = timezone.now().date() - timedelta(days=45)
        vehicule = self.creer_vehicule(date_achat=achat)
        self.assertEqual(vehicule.jours_detention, 45)


class TableauDeBordTests(BaseVehiculeTests):
    def setUp(self):
        super().setUp()
        self.url = reverse('vehicules:tableau-de-bord')
        aujourdhui = timezone.now().date()

        # En stock depuis 120 jours : dormant (seuil 90 j)
        self.dormant = self.creer_vehicule(date_achat=aujourdhui - timedelta(days=120))
        RemiseEnEtat.objects.create(vehicule=self.dormant, montant=Decimal('500'))

        # En stock depuis 10 jours : frais
        self.recent = self.creer_vehicule(date_achat=aujourdhui - timedelta(days=10))

        # Vendu il y a 5 jours, avec marge
        self.vendu = self.creer_vehicule(
            date_achat=aujourdhui - timedelta(days=35),
            date_vente=aujourdhui - timedelta(days=5),
            prix_vente=Decimal('14000'),
        )
        RemiseEnEtat.objects.create(vehicule=self.vendu, montant=Decimal('200'))

        # Vendu il y a 3 ans : hors période par défaut (12 mois glissants)
        self.vendu_ancien = self.creer_vehicule(
            date_achat=aujourdhui - timedelta(days=1100),
            date_vente=aujourdhui - timedelta(days=1080),
            prix_vente=Decimal('9000'),
        )

        self.client.force_login(self.user)
        session = self.client.session
        session[GARAGE_SESSION_KEY] = self.garage.id
        session.save()

    def contexte(self, **params):
        return self.client.get(self.url, params).context

    def test_page_accessible(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_anonyme_redirige(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_bloc_stock_ignore_les_vendus(self):
        stock = self.contexte()['stock']
        self.assertEqual(stock['nb'], 2)
        # (10000 + 500 + 300) x 2 + 500 de remise sur le dormant
        self.assertEqual(stock['valeur'], Decimal('22100'))
        self.assertEqual(stock['age_moyen'], 65)   # moyenne de 120 et 10

    def test_stock_dormant_au_dela_du_seuil(self):
        stock = self.contexte()['stock']
        self.assertEqual(stock['nb_dormant'], 1)
        self.assertEqual(stock['capital_dormant'], Decimal('11300'))

    def test_le_stock_ne_depend_pas_de_la_periode(self):
        """Filtrer sur le mois en cours ne doit rien changer au stock détenu."""
        self.assertEqual(self.contexte()['stock'], self.contexte(periode='mois')['stock'])

    def test_activite_bornee_par_la_periode(self):
        activite = self.contexte()['activite']
        self.assertEqual(activite['nb'], 1)
        self.assertEqual(activite['ca'], Decimal('14000'))
        self.assertEqual(activite['marge'], Decimal('3000'))       # 14000 - 10800 - 200
        self.assertEqual(activite['marge_fiscale'], Decimal('3200'))
        self.assertEqual(activite['rotation'], 30)

    def test_periode_tout_reprend_les_ventes_anciennes(self):
        self.assertEqual(self.contexte(periode='tout')['activite']['nb'], 2)

    def test_periode_personnalisee(self):
        aujourdhui = timezone.now().date()
        activite = self.contexte(
            periode='perso',
            du=(aujourdhui - timedelta(days=10)).isoformat(),
            au=aujourdhui.isoformat(),
        )['activite']
        self.assertEqual(activite['nb'], 1)

    def test_periode_invalide_retombe_sur_douze_mois(self):
        self.assertEqual(self.contexte(periode='nimportequoi')['f_periode'], '12mois')

    def test_marque_non_numerique_ignoree(self):
        """?marque=abc ne doit pas remonter en ValueError."""
        reponse = self.client.get(self.url, {'marque': 'abc'})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context['stock']['nb'], 2)

    def test_filtre_energie_reduit_le_stock(self):
        self.recent.energie = Vehicule.Energie.DIESEL
        self.recent.save()
        self.assertEqual(self.contexte(energie='essence')['stock']['nb'], 1)

    def test_ventes_a_perte_reperees(self):
        self.vendu.prix_vente = Decimal('9000')
        self.vendu.save()
        contexte = self.contexte()
        self.assertEqual(contexte['nb_ventes_a_perte'], 1)
        self.assertEqual(contexte['activite']['marge'], Decimal('-2000'))

    def test_un_autre_garage_reste_invisible(self):
        autre = creer_garage('Garage Voisin')
        self.creer_vehicule(garage=autre)

        # Garage actif : le véhicule du voisin n'est pas compté
        self.assertEqual(self.contexte()['stock']['nb'], 2)
        # Même en demandant « tous les garages » : l'utilisateur n'est pas membre du voisin
        self.assertEqual(self.contexte(garage='tous')['stock']['nb'], 2)


# ═══════════════════ EXPORTS ═══════════════════

class BornesPeriodeTests(TestCase):
    """« Mois dernier » est la seule période que le tableau de bord n'utilisait pas."""

    def test_mois_dernier_en_milieu_d_annee(self):
        debut, fin = bornes_periode('mois_dernier', date(2026, 8, 14))
        self.assertEqual(debut, date(2026, 7, 1))
        self.assertEqual(fin, date(2026, 7, 31))

    def test_mois_dernier_bascule_sur_l_annee_precedente(self):
        # Le piège : en janvier, le mois dernier est en décembre de l'année d'avant.
        debut, fin = bornes_periode('mois_dernier', date(2026, 1, 15))
        self.assertEqual(debut, date(2025, 12, 1))
        self.assertEqual(fin, date(2025, 12, 31))

    def test_mois_dernier_apres_un_mois_de_fevrier(self):
        debut, fin = bornes_periode('mois_dernier', date(2024, 3, 5))
        self.assertEqual(debut, date(2024, 2, 1))
        self.assertEqual(fin, date(2024, 2, 29))   # année bissextile

    def test_code_inconnu_reste_sans_borne(self):
        self.assertEqual(bornes_periode('n_importe_quoi', date(2026, 8, 14)), (None, None))


class SyntheseTests(BaseVehiculeTests):
    """Les ventes se bornent sur la date de vente, les achats sur la date d'achat."""

    def setUp(self):
        super().setUp()
        # Acheté ET vendu en juin
        self.vendu_juin = self.creer_vehicule(
            date_achat=date(2026, 6, 3), date_vente=date(2026, 6, 20),
            prix_vente=Decimal('14000'),
        )
        RemiseEnEtat.objects.create(vehicule=self.vendu_juin, montant=Decimal('200'))

        # Acheté en juin, vendu en juillet : compte dans les achats de juin
        # et dans les ventes de juillet, mais jamais dans les deux à la fois.
        self.achete_juin = self.creer_vehicule(
            date_achat=date(2026, 6, 25), date_vente=date(2026, 7, 4),
            prix_vente=Decimal('12000'),
        )

        # Toujours en stock
        self.en_stock = self.creer_vehicule(date_achat=date(2026, 6, 10))

    def synthese_juin(self):
        return synthese(
            Vehicule.objects.filter(garage=self.garage).avec_couts(),
            date(2026, 6, 1), date(2026, 6, 30), date(2026, 8, 14),
        )

    def test_ventes_bornees_sur_la_date_de_vente(self):
        donnees = self.synthese_juin()
        self.assertEqual(donnees['nb_vendus'], 1)
        self.assertEqual([v.pk for v in donnees['ventes']], [self.vendu_juin.pk])

    def test_achats_bornes_sur_la_date_d_achat(self):
        # Les trois véhicules ont été achetés en juin, même celui vendu en juillet.
        self.assertEqual(self.synthese_juin()['nb_achetes'], 3)

    def test_stock_ignore_la_periode(self):
        # Un seul véhicule est encore en stock, quelle que soit la période demandée.
        self.assertEqual(self.synthese_juin()['nb_stock'], 1)
        sans_borne = synthese(
            Vehicule.objects.filter(garage=self.garage).avec_couts(),
            None, None, date(2026, 8, 14),
        )
        self.assertEqual(sans_borne['nb_stock'], 1)

    def test_marge_deduit_les_frais_de_remise_en_etat(self):
        # 14000 - (10000 + 500 + 300) - 200 de remise en état
        self.assertEqual(self.synthese_juin()['marge'], Decimal('3000.00'))

    def test_totaux_alignes_sur_les_lignes(self):
        donnees = self.synthese_juin()
        self.assertEqual(donnees['totaux']['prix_achat'], Decimal('10800.00'))
        self.assertEqual(donnees['totaux']['frais'], Decimal('200.00'))
        self.assertEqual(donnees['totaux']['prix_vente'], Decimal('14000.00'))
        self.assertEqual(donnees['totaux']['marge'], Decimal('3000.00'))

    def test_periode_vide_ne_plante_pas(self):
        donnees = synthese(
            Vehicule.objects.filter(garage=self.garage).avec_couts(),
            date(2020, 1, 1), date(2020, 12, 31), date(2026, 8, 14),
        )
        self.assertEqual(donnees['nb_vendus'], 0)
        self.assertEqual(donnees['marge'], Decimal('0.00'))
        self.assertEqual(donnees['totaux']['marge'], Decimal('0.00'))


class EcrituresComptablesTests(BaseVehiculeTests):
    """Le régime de la TVA sur la marge : trois lignes par vente, équilibrées."""

    def setUp(self):
        super().setUp()
        self.parametrage = ParametrageComptable.objects.create(
            garage=self.garage,
            compte_ventes_totales='707000000',
            compte_ventes_prix_achat='707010000',
            compte_tva_collectee='445710090',
            taux_tva=Decimal('20.00'),
        )

    def vente_du_modele(self):
        """Le cas exact du modèle fourni : achat 4 123, vente 6 600."""
        return self.creer_vehicule(
            prix_vehicule='4123', prix_enchere='0', prix_transport='0',
            date_achat=date(2025, 5, 2), date_vente=date(2025, 10, 17),
            prix_vente=Decimal('6600'), acheteur='BELIGNI DUILIO',
            numero_vente=38160,
        )

    def lignes(self, parametrage=None):
        ventes = Vehicule.objects.filter(garage=self.garage).avec_couts().vendus()
        return lignes_ecritures(list(ventes), parametrage or self.parametrage)

    def test_reproduit_le_modele_au_centime(self):
        self.vente_du_modele()
        lignes = self.lignes()

        self.assertEqual(len(lignes), 3)
        self.assertEqual(lignes[0].compte, '707000000')
        self.assertEqual(lignes[0].debit, Decimal('2477.00'))
        self.assertEqual(lignes[0].credit, Decimal('0.00'))
        self.assertEqual(lignes[1].compte, '707010000')
        self.assertEqual(lignes[1].credit, Decimal('2064.17'))
        self.assertEqual(lignes[2].compte, '445710090')
        self.assertEqual(lignes[2].credit, Decimal('412.83'))

    def test_ecriture_equilibree(self):
        self.vente_du_modele()
        lignes = self.lignes()
        self.assertEqual(lignes[0].debit, lignes[1].credit + lignes[2].credit)

    def test_libelle_et_piece(self):
        self.vente_du_modele()
        ligne = self.lignes()[0]
        self.assertEqual(ligne.libelle, 'BELIGNI DUILIO Renault Clio AA-001-AA')
        self.assertEqual(ligne.piece, 38160)
        self.assertEqual(ligne.date, date(2025, 10, 17))

    def test_libelle_sans_acheteur(self):
        self.creer_vehicule(
            date_vente=date(2025, 10, 17), prix_vente=Decimal('14000'),
        )
        self.assertEqual(self.lignes()[0].libelle, 'Renault Clio AA-001-AA')

    def test_taux_non_entier_respecte(self):
        # 5,50 n'est pas le taux applicable aux véhicules d'occasion : c'est
        # justement l'intérêt. En testant avec le taux par défaut (20 %), on
        # ne saurait pas distinguer « le code lit le paramétrage du garage »
        # de « le code applique 20 % en dur ». Il faut une valeur qui diffère
        # du défaut, et à décimales, pour éprouver aussi les arrondis.
        self.parametrage.taux_tva = Decimal('5.50')
        self.parametrage.save()
        self.vente_du_modele()
        lignes = self.lignes()
        # 2477 / 1,055 = 2347,87 ; la TVA se déduit par différence
        self.assertEqual(lignes[1].credit, Decimal('2347.87'))
        self.assertEqual(lignes[2].credit, Decimal('129.13'))
        self.assertEqual(lignes[0].debit, lignes[1].credit + lignes[2].credit)

    def test_comptes_du_garage_et_non_les_defauts(self):
        self.parametrage.compte_ventes_totales = '701000000'
        self.parametrage.compte_tva_collectee = '445711111'
        self.parametrage.save()
        self.vente_du_modele()
        lignes = self.lignes()
        self.assertEqual(lignes[0].compte, '701000000')
        self.assertEqual(lignes[2].compte, '445711111')

    def test_vente_a_perte_ecartee(self):
        # Revendu moins cher qu'acheté : sans marge, pas de TVA sur la marge.
        self.creer_vehicule(
            date_vente=date(2025, 10, 17), prix_vente=Decimal('5000'),
        )
        self.assertEqual(self.lignes(), [])

    def test_marge_nulle_ecartee(self):
        self.creer_vehicule(
            prix_vehicule='6600', prix_enchere='0', prix_transport='0',
            date_vente=date(2025, 10, 17), prix_vente=Decimal('6600'),
        )
        self.assertEqual(self.lignes(), [])

    def test_ventes_ecartees_sont_signalees(self):
        perdant = self.creer_vehicule(
            date_vente=date(2025, 10, 17), prix_vente=Decimal('5000'),
        )
        self.vente_du_modele()
        ventes = list(Vehicule.objects.filter(garage=self.garage).avec_couts().vendus())
        self.assertEqual([v.pk for v in ventes_ecartees(ventes)], [perdant.pk])


class CsvComptableTests(BaseVehiculeTests):
    def setUp(self):
        super().setUp()
        self.parametrage = ParametrageComptable.pour(self.garage)
        self.creer_vehicule(
            prix_vehicule='4123', prix_enchere='0', prix_transport='0',
            date_vente=date(2025, 10, 17), prix_vente=Decimal('6600'),
            acheteur='BELIGNI DUILIO', numero_vente=38160,
        )

    def contenu(self):
        ventes = list(Vehicule.objects.filter(garage=self.garage).avec_couts().vendus())
        return ecrire_csv(lignes_ecritures(ventes, self.parametrage))

    def test_ligne_d_entete(self):
        # Les intitulés servent au logiciel de comptabilité pour reconnaître
        # les colonnes à l'import : ils font partie du contrat du fichier.
        premiere = self.contenu().decode('utf-8-sig').splitlines()[0]
        self.assertEqual(premiere, 'date;compte;libelle;Numero de piece;debit;credit')

    def test_colonnes_et_format_des_montants(self):
        lignes = self.contenu().decode('utf-8-sig').splitlines()
        self.assertEqual(
            lignes[1],
            '17/10/2025;707000000;BELIGNI DUILIO Renault Clio AA-001-AA;38160;2477,00;0,00',
        )
        self.assertEqual(
            lignes[2],
            '17/10/2025;707010000;BELIGNI DUILIO Renault Clio AA-001-AA;38160;0,00;2064,17',
        )

    def test_une_seule_ligne_d_entete(self):
        # Trois écritures pour une vente, plus l'en-tête.
        self.assertEqual(len(self.contenu().decode('utf-8-sig').splitlines()), 4)

    def test_bom_utf8_pour_excel(self):
        # Sans le BOM, Excel en français ouvre le fichier en latin-1 et abîme les accents.
        self.assertTrue(self.contenu().startswith(b'\xef\xbb\xbf'))

    def test_fins_de_ligne_crlf(self):
        self.assertIn(b'\r\n', self.contenu())

    def test_entete_seule_si_aucune_vente(self):
        # Un fichier réduit à ses intitulés s'importe sans erreur, là où un
        # fichier totalement vide fait souvent échouer l'import.
        Vehicule.objects.all().update(date_vente=None, prix_vente=None)
        lignes = self.contenu().decode('utf-8-sig').splitlines()
        self.assertEqual(lignes, ['date;compte;libelle;Numero de piece;debit;credit'])


class ParametrageComptableModeleTests(BaseVehiculeTests):
    def test_pour_renvoie_les_defauts_sans_ecrire_en_base(self):
        parametrage = ParametrageComptable.pour(self.garage)
        self.assertIsNone(parametrage.pk)
        self.assertEqual(parametrage.compte_ventes_totales, '707000000')
        self.assertEqual(parametrage.taux_tva, Decimal('20.00'))
        self.assertEqual(ParametrageComptable.objects.count(), 0)

    def test_pour_renvoie_l_enregistrement_existant(self):
        ParametrageComptable.objects.create(garage=self.garage, taux_tva=Decimal('5.50'))
        self.assertEqual(ParametrageComptable.pour(self.garage).taux_tva, Decimal('5.50'))


class VuesExportTests(BaseVehiculeTests):
    def setUp(self):
        super().setUp()
        aujourdhui = timezone.now().date()
        self.vendu = self.creer_vehicule(
            date_achat=aujourdhui - timedelta(days=40),
            date_vente=aujourdhui - timedelta(days=2),
            prix_vente=Decimal('14000'),
        )
        self.client.force_login(self.user)
        session = self.client.session
        session[GARAGE_SESSION_KEY] = self.garage.id
        session.save()

    def test_page_exports_accessible(self):
        reponse = self.client.get(reverse('vehicules:exports'))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context['donnees']['nb_vendus'], 1)

    def test_pdf_est_un_pdf_telecharge(self):
        reponse = self.client.get(reverse('vehicules:export-synthese-pdf'))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse['Content-Type'], 'application/pdf')
        self.assertIn('attachment', reponse['Content-Disposition'])
        self.assertTrue(reponse.content.startswith(b'%PDF'))

    def test_pdf_sur_periode_vide(self):
        reponse = self.client.get(
            reverse('vehicules:export-synthese-pdf'),
            {'periode': 'perso', 'du': '2019-01-01', 'au': '2019-12-31'},
        )
        self.assertTrue(reponse.content.startswith(b'%PDF'))

    def test_csv_telecharge(self):
        reponse = self.client.get(reverse('vehicules:export-comptable-csv'))
        self.assertEqual(reponse.status_code, 200)
        self.assertIn('attachment', reponse['Content-Disposition'])
        self.assertIn('ecritures', reponse['Content-Disposition'])
        self.assertTrue(reponse.content.startswith(b'\xef\xbb\xbf'))

    def test_periode_bricolee_ne_plante_pas(self):
        reponse = self.client.get(reverse('vehicules:exports'), {'periode': 'n_importe_quoi'})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.context['f_periode'], 'mois')

    def test_dates_perso_illisibles_ne_plantent_pas(self):
        reponse = self.client.get(
            reverse('vehicules:exports'), {'periode': 'perso', 'du': 'hier', 'au': ''},
        )
        self.assertEqual(reponse.status_code, 200)

    def test_anonyme_redirige(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('vehicules:exports')).status_code, 302)

    def test_le_garage_du_voisin_ne_fuit_pas(self):
        voisin = creer_garage('Garage Voisin')
        self.creer_vehicule(
            garage=voisin, date_vente=timezone.now().date(), prix_vente=Decimal('30000'),
        )
        # Le périmètre est le garage actif : la vente du voisin est invisible.
        reponse = self.client.get(reverse('vehicules:exports'))
        self.assertEqual(reponse.context['donnees']['nb_vendus'], 1)


class DroitsExportTests(BaseVehiculeTests):
    """Exporter est de la lecture ; régler les comptes est de l'écriture."""

    def setUp(self):
        super().setUp()
        self.lecteur = User.objects.create_user(
            email='lecteur@test.fr', password='x', first_name='L', last_name='L',
        )
        GarageMembre.objects.create(
            user=self.lecteur, garage=self.garage, role=GarageMembre.Role.LECTURE,
        )
        self._connecter(self.lecteur)

    def _connecter(self, user):
        self.client.force_login(user)
        session = self.client.session
        session[GARAGE_SESSION_KEY] = self.garage.id
        session.save()

    def test_lecteur_peut_exporter(self):
        for nom in ('exports', 'export-synthese-pdf', 'export-comptable-csv'):
            with self.subTest(vue=nom):
                self.assertEqual(self.client.get(reverse(f'vehicules:{nom}')).status_code, 200)

    def test_lecteur_ne_peut_pas_parametrer(self):
        reponse = self.client.get(reverse('garages:parametrage-comptable'))
        self.assertEqual(reponse.status_code, 403)

    def test_lien_de_parametrage_masque_au_lecteur(self):
        reponse = self.client.get(reverse('vehicules:exports'))
        self.assertNotContains(reponse, reverse('garages:parametrage-comptable'))

    def test_gestionnaire_peut_parametrer(self):
        self._connecter(self.user)
        self.assertEqual(
            self.client.get(reverse('garages:parametrage-comptable')).status_code, 200,
        )

    def test_gestionnaire_enregistre_le_parametrage(self):
        self._connecter(self.user)
        reponse = self.client.post(reverse('garages:parametrage-comptable'), {
            'compte_ventes_totales': '701000000',
            'compte_ventes_prix_achat': '701010000',
            'compte_tva_collectee': '445711111',
            'taux_tva': '5.50',
        })
        self.assertEqual(reponse.status_code, 302)
        parametrage = ParametrageComptable.objects.get(garage=self.garage)
        self.assertEqual(parametrage.compte_ventes_totales, '701000000')
        self.assertEqual(parametrage.taux_tva, Decimal('5.50'))

    def test_compte_non_numerique_refuse(self):
        self._connecter(self.user)
        reponse = self.client.post(reverse('garages:parametrage-comptable'), {
            'compte_ventes_totales': '70A000000',
            'compte_ventes_prix_achat': '707010000',
            'compte_tva_collectee': '445710090',
            'taux_tva': '20',
        })
        self.assertEqual(reponse.status_code, 200)   # réaffiché avec l'erreur
        self.assertFalse(ParametrageComptable.objects.exists())


class StockALaDateTests(BaseVehiculeTests):
    """Une photo à une date passée, qui n'est pas le stock d'aujourd'hui."""

    def setUp(self):
        super().setUp()
        # Acheté avant, vendu après : détenu au 30/06
        self.detenu = self.creer_vehicule(
            date_achat=date(2025, 3, 1),
            date_vente=date(2025, 9, 1), prix_vente=Decimal('14000'),
        )
        RemiseEnEtat.objects.create(vehicule=self.detenu, montant=Decimal('400'))

        # Acheté avant, vendu avant : plus détenu au 30/06
        self.deja_vendu = self.creer_vehicule(
            date_achat=date(2025, 1, 5),
            date_vente=date(2025, 5, 20), prix_vente=Decimal('12000'),
        )

        # Acheté après : pas encore détenu au 30/06
        self.pas_encore = self.creer_vehicule(date_achat=date(2025, 8, 1))

        # Jamais vendu : détenu au 30/06 et encore aujourd'hui
        self.toujours = self.creer_vehicule(date_achat=date(2025, 2, 10))

    def au(self, jour):
        return stock_a_la_date(
            Vehicule.objects.filter(garage=self.garage).avec_couts(), jour,
        )

    def test_photo_a_une_date_passee(self):
        donnees = self.au(date(2025, 6, 30))
        self.assertEqual(
            [v.pk for v in donnees['lignes']],
            [self.toujours.pk, self.detenu.pk],   # ordre d'acquisition : 10/02 puis 01/03
        )
        self.assertEqual(donnees['nb'], 2)

    def test_un_vehicule_vendu_depuis_compte_quand_meme(self):
        # Le piège : self.detenu est vendu aujourd'hui, mais il était bien
        # en stock au 30/06. en_stock() l'exclurait à tort.
        self.assertIn(self.detenu, self.au(date(2025, 6, 30))['lignes'])
        self.assertNotIn(self.detenu, self.au(date(2025, 12, 31))['lignes'])

    def test_vente_le_jour_meme_sort_du_stock(self):
        # Vendu le 20/05 : détenu le 19, plus détenu le 20.
        self.assertIn(self.deja_vendu, self.au(date(2025, 5, 19))['lignes'])
        self.assertNotIn(self.deja_vendu, self.au(date(2025, 5, 20))['lignes'])

    def test_achat_le_jour_meme_entre_en_stock(self):
        self.assertNotIn(self.pas_encore, self.au(date(2025, 7, 31))['lignes'])
        self.assertIn(self.pas_encore, self.au(date(2025, 8, 1))['lignes'])

    def test_tri_par_ordre_d_acquisition(self):
        dates = [v.date_achat for v in self.au(date(2026, 1, 1))['lignes']]
        self.assertEqual(dates, sorted(dates))

    def test_totaux(self):
        donnees = self.au(date(2025, 6, 30))
        # deux véhicules à 10800 de prix d'achat, dont un avec 400 de frais
        self.assertEqual(donnees['totaux']['prix_achat'], Decimal('21600.00'))
        self.assertEqual(donnees['totaux']['frais'], Decimal('400.00'))
        self.assertEqual(donnees['totaux']['cout'], Decimal('22000.00'))

    def test_date_sans_aucun_vehicule(self):
        donnees = self.au(date(2020, 1, 1))
        self.assertEqual(donnees['nb'], 0)
        self.assertEqual(donnees['totaux']['cout'], Decimal('0.00'))


class VueExportStockTests(BaseVehiculeTests):
    def setUp(self):
        super().setUp()
        self.creer_vehicule(date_achat=date(2025, 3, 1))
        self.client.force_login(self.user)
        session = self.client.session
        session[GARAGE_SESSION_KEY] = self.garage.id
        session.save()
        self.url = reverse('vehicules:export-stock-pdf')

    def test_pdf_telecharge(self):
        reponse = self.client.get(self.url, {'stock_au': '2025-06-30'})
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse['Content-Type'], 'application/pdf')
        self.assertIn('etat-stock-2025-06-30.pdf', reponse['Content-Disposition'])
        self.assertTrue(reponse.content.startswith(b'%PDF'))

    def test_sans_date_prend_aujourdhui(self):
        reponse = self.client.get(self.url)
        aujourdhui = timezone.now().date().isoformat()
        self.assertIn(f'etat-stock-{aujourdhui}.pdf', reponse['Content-Disposition'])

    def test_date_illisible_retombe_sur_aujourdhui(self):
        reponse = self.client.get(self.url, {'stock_au': 'avant-hier'})
        self.assertEqual(reponse.status_code, 200)
        self.assertTrue(reponse.content.startswith(b'%PDF'))

    def test_date_sans_stock_produit_un_pdf_valide(self):
        reponse = self.client.get(self.url, {'stock_au': '2019-01-01'})
        self.assertTrue(reponse.content.startswith(b'%PDF'))

    def test_le_garage_du_voisin_ne_fuit_pas(self):
        voisin = creer_garage('Garage Voisin')
        self.creer_vehicule(garage=voisin, date_achat=date(2025, 1, 1))
        contexte = self.client.get(reverse('vehicules:exports')).context
        self.assertEqual(contexte['stock']['nb'], 1)
