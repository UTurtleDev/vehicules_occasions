"""
Construction des deux exports, sans rien savoir de HTTP.

Les fonctions d'ici prennent des querysets et rendent des données ; ce sont
les vues qui les emballent dans une réponse. Elles se testent donc
directement, sans client de test.
"""

import csv
import io
from collections import namedtuple
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q, Sum

CENT = Decimal('0.01')
ZERO = Decimal('0.00')

# Les périodes proposées par les exports. Volontairement plus courte que la
# liste PERIODES du tableau de bord : un export comptable se raisonne en mois
# clos, pas en « 12 derniers mois ».
PERIODES_EXPORT = [
    ('mois',         'Mois en cours'),
    ('mois_dernier', 'Mois dernier'),
    ('annee',        'Année en cours'),
    ('perso',        'Période personnalisée'),
]

PERIODE_DEFAUT = 'mois'

LigneEcriture = namedtuple('LigneEcriture', 'date compte libelle piece debit credit')

# En-tête du CSV, repris tel quel du modèle fourni par le comptable.
#
# Volontairement SANS ACCENTS : c'est à cette condition que le logiciel de
# comptabilité reconnaît les colonnes tout seul à l'import. Avec des
# accents, il faut les associer une à une à la main à chaque import.
# « Numero de piece » n'est donc pas une faute de frappe, ne pas corriger.
#
# Seuls les intitulés sont concernés. Le contenu de la colonne libellé
# vient de la base et garde ses accents (« Mme Lefèvre »), le BOM UTF-8
# suffit à les faire passer.
ENTETES_CSV = ['date', 'compte', 'libelle', 'Numero de piece', 'debit', 'credit']


def libelle_periode(code, debut, fin):
    """Intitulé lisible de la période, pour la page et pour l'en-tête du PDF."""
    if code != 'perso':
        return dict(PERIODES_EXPORT).get(code, '')
    if debut and fin:
        return f'Du {debut:%d/%m/%Y} au {fin:%d/%m/%Y}'
    if debut:
        return f'À partir du {debut:%d/%m/%Y}'
    if fin:
        return f"Jusqu'au {fin:%d/%m/%Y}"
    return 'Depuis le début'


def suffixe_fichier(debut, fin, aujourdhui):
    """
    Fragment de date qui rend un fichier téléchargé reconnaissable.

    Un mois complet donne « 2026-08 » ; toute autre plage donne ses deux
    bornes, pour qu'on ne confonde pas deux exports dans un dossier.
    """
    if debut and fin:
        meme_mois = (debut.year, debut.month) == (fin.year, fin.month)
        if meme_mois and debut.day == 1:
            return f'{debut:%Y-%m}'
        return f'{debut:%Y-%m-%d}_{fin:%Y-%m-%d}'
    return f'{aujourdhui:%Y-%m-%d}'


def arrondir(montant):
    """
    Ramène un montant à deux décimales.

    Indispensable avant tout affichage ou écriture : SQLite n'ayant pas de
    vrai type DECIMAL, les valeurs annotées ressortent avec du bruit flottant
    (383.700000000001). Invisible à l'écran via le filtre |euros, mais bien
    présent dans un CSV lu par un logiciel de comptabilité.
    """
    return Decimal(montant or 0).quantize(CENT, rounding=ROUND_HALF_UP)


# ═══════════════════ SYNTHÈSE DIRIGEANT ═══════════════════

def synthese(qs, debut, fin, aujourdhui):
    """
    Chiffres de la synthèse des ventes.

    `qs` doit déjà être restreint au garage voulu et être passé par
    avec_couts(). Les bornes sont inclusives, et None signifie « pas de
    borne », comme partout ailleurs dans l'application.

    Deux bornages différents cohabitent volontairement : les ventes se
    comptent sur date_vente, les achats sur date_achat. Un véhicule acheté
    en mars et vendu en avril compte donc dans les achats de mars et dans
    les ventes d'avril, ce qui est bien le comportement attendu.
    """
    vendus = qs.vendus()
    achetes = qs
    if debut:
        vendus = vendus.filter(date_vente__gte=debut)
        achetes = achetes.filter(date_achat__gte=debut)
    if fin:
        vendus = vendus.filter(date_vente__lte=fin)
        achetes = achetes.filter(date_achat__lte=fin)

    # Tri par pk en second critère : sans lui, deux ventes du même jour
    # sortiraient dans un ordre indéterminé, et deux exports identiques
    # pourraient différer.
    ventes = list(
        vendus.select_related('marque', 'modele').order_by('date_vente', 'pk')
    )

    totaux = vendus.aggregate(
        prix_achat=Sum('prix_achat_calc'),
        frais=Sum('frais_reel_calc'),
        prix_vente=Sum('prix_vente'),
        marge=Sum('marge_interne_calc'),
    )

    return {
        'ventes': ventes,
        'totaux': {cle: arrondir(valeur) for cle, valeur in totaux.items()},
        'nb_vendus': len(ventes),
        'nb_achetes': achetes.count(),
        'marge': arrondir(totaux['marge']),
        # Photo à ce jour : le stock ne se filtre pas sur la période, sinon
        # « véhicules en stock au mois dernier » ne voudrait rien dire.
        'nb_stock': qs.en_stock().count(),
    }


# ═══════════════════ STOCK À UNE DATE ═══════════════════

def stock_a_la_date(qs, a_la_date):
    """
    Véhicules détenus à une date donnée, par ordre d'acquisition.

    Ce n'est pas `en_stock()`, qui répond « pas encore vendu à ce jour ».
    Un véhicule était détenu à une date s'il était acheté à cette date et
    pas encore vendu à cette date : un véhicule vendu depuis compte donc
    quand même, dès lors que la vente est postérieure. C'est ce qui permet
    de reconstituer un état de stock passé, par exemple à une clôture.

    Attention : les frais de remise en état ne portent pas de date en base,
    la colonne « frais » est donc le total des frais du véhicule, y compris
    ceux engagés après `a_la_date`.
    """
    detenus = qs.filter(date_achat__lte=a_la_date).filter(
        Q(date_vente__isnull=True) | Q(date_vente__gt=a_la_date)
    )

    lignes = list(
        detenus.select_related('marque', 'modele').order_by('date_achat', 'pk')
    )
    totaux = detenus.aggregate(
        prix_achat=Sum('prix_achat_calc'),
        frais=Sum('frais_reel_calc'),
        cout=Sum('cout_revient_calc'),
    )

    return {
        'lignes': lignes,
        'nb': len(lignes),
        'totaux': {cle: arrondir(valeur) for cle, valeur in totaux.items()},
    }


# ═══════════════════ ÉCRITURES COMPTABLES ═══════════════════

def ventiler_marge(marge_ttc, taux_tva):
    """
    Éclate une marge TTC en (marge TTC, marge HT, TVA).

    La TVA se déduit par différence plutôt que de se calculer pour
    elle-même : c'est ce qui garantit que HT + TVA redonne exactement le
    TTC, sans centime perdu dans les arrondis, quel que soit le taux.
    """
    marge_ttc = arrondir(marge_ttc)
    marge_ht = arrondir(marge_ttc / (1 + Decimal(taux_tva) / 100))
    return marge_ttc, marge_ht, marge_ttc - marge_ht


def est_exportable(vehicule):
    """
    Une vente ne donne lieu à écriture que si elle dégage une marge positive.

    Sans marge, pas de TVA sur la marge à collecter : produire l'écriture
    quand même inventerait une TVA négative. Ces ventes sont signalées à
    l'utilisateur plutôt que supprimées en silence.
    """
    return vehicule.prix_vente is not None and (vehicule.marge_fiscale_calc or 0) > 0


def libelle_vehicule(vehicule):
    """« BELIGNI DUILIO FIAT PANDA DR-016-AL »"""
    morceaux = [
        vehicule.acheteur,
        str(vehicule.marque),
        str(vehicule.modele),
        vehicule.immatriculation,
    ]
    return ' '.join(m for m in morceaux if m)


def lignes_ecritures(ventes, parametrage):
    """Trois lignes par vente : marge TTC au débit, marge HT et TVA au crédit."""
    lignes = []

    for vehicule in ventes:
        if not est_exportable(vehicule):
            continue

        marge_ttc, marge_ht, tva = ventiler_marge(
            vehicule.marge_fiscale_calc, parametrage.taux_tva,
        )
        libelle = libelle_vehicule(vehicule)
        # Test sur None et non sur la fausseté : un numéro de pièce valant 0
        # est un numéro, « or '' » l'effacerait.
        piece = '' if vehicule.numero_vente is None else vehicule.numero_vente

        lignes.extend([
            LigneEcriture(
                vehicule.date_vente, parametrage.compte_ventes_totales,
                libelle, piece, marge_ttc, ZERO,
            ),
            LigneEcriture(
                vehicule.date_vente, parametrage.compte_ventes_prix_achat,
                libelle, piece, ZERO, marge_ht,
            ),
            LigneEcriture(
                vehicule.date_vente, parametrage.compte_tva_collectee,
                libelle, piece, ZERO, tva,
            ),
        ])

    return lignes


def ventes_ecartees(ventes):
    """Ventes absentes de l'écriture, à signaler sur la page d'export."""
    return [v for v in ventes if not est_exportable(v)]


def montant_csv(montant):
    """2477.00 → « 2477,00 ». Virgule décimale, pas de milliers, pas d'euro."""
    return f'{montant:.2f}'.replace('.', ',')


def ecrire_csv(lignes):
    """
    Sérialise les écritures, prêtes à ouvrir dans Excel.

    La première ligne nomme les colonnes : c'est ce qui permet au logiciel
    de comptabilité de les reconnaître à l'import. Le BOM (utf-8-sig) fait
    qu'Excel reconnaît l'UTF-8 tout seul, sans passer par l'assistant
    d'importation.
    """
    tampon = io.StringIO()
    graveur = csv.writer(tampon, delimiter=';', lineterminator='\r\n')
    graveur.writerow(ENTETES_CSV)

    for ligne in lignes:
        graveur.writerow([
            ligne.date.strftime('%d/%m/%Y'),
            ligne.compte,
            ligne.libelle,
            ligne.piece,
            montant_csv(ligne.debit),
            montant_csv(ligne.credit),
        ])

    return tampon.getvalue().encode('utf-8-sig')
