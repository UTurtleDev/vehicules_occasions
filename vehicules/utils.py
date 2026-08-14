"""
Helpers de période et de calcul partagés entre le tableau de bord et les
exports. Ils vivaient dans views.py ; ils en ont été sortis pour que les
exports puissent s'en servir sans importer les vues.
"""

from datetime import date, timedelta

PERIODES = [
    ('mois',      'Mois en cours'),
    ('trimestre', 'Trimestre en cours'),
    ('annee',     'Année en cours'),
    ('12mois',    '12 derniers mois'),
    ('tout',      'Depuis le début'),
]


def bornes_periode(code, aujourdhui):
    """Renvoie (début, fin) de la période. (None, None) signifie sans borne."""
    if code == 'mois':
        return aujourdhui.replace(day=1), aujourdhui
    if code == 'mois_dernier':
        # Le dernier jour du mois précédent, c'est la veille du premier jour
        # de celui-ci : on évite ainsi de compter les jours du mois et de
        # gérer la bascule de décembre à janvier à la main.
        fin = aujourdhui.replace(day=1) - timedelta(days=1)
        return fin.replace(day=1), fin
    if code == 'trimestre':
        premier_mois = 3 * ((aujourdhui.month - 1) // 3) + 1
        return aujourdhui.replace(month=premier_mois, day=1), aujourdhui
    if code == 'annee':
        return aujourdhui.replace(month=1, day=1), aujourdhui
    if code == '12mois':
        return aujourdhui - timedelta(days=365), aujourdhui
    return None, None


def date_ou_none(texte):
    """Lit une date d'un champ <input type="date">, sans planter si elle est absente ou bricolée."""
    try:
        return date.fromisoformat(texte)
    except (TypeError, ValueError):
        return None


def moyenne_entiere(valeurs):
    valeurs = list(valeurs)
    return round(sum(valeurs) / len(valeurs)) if valeurs else None


def pourcentage(part, total):
    return round(part / total * 100, 1) if total else None
