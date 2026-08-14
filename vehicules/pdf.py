"""
Rendu PDF de la synthèse des ventes.

Seul module à connaître ReportLab : exports.py produit les chiffres, ce
fichier les met en page. Changer de moteur PDF ne toucherait que lui.

Parti pris visuel : noir sur blanc. Pas de reprise du thème sombre de
l'application, illisible à l'impression et vorace en encre, ni de l'accent
doré, dont le contraste sur fond blanc est mauvais et qui disparaît sur une
imprimante en niveaux de gris. La hiérarchie passe donc par la graisse, la
taille et un gris moyen.
"""

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from vehicules.templatetags.vo_filters import euros

NOIR = colors.HexColor('#111111')
GRIS = colors.HexColor('#666666')
GRIS_CLAIR = colors.HexColor('#DDDDDD')
GRIS_FOND = colors.HexColor('#F2F2F2')
ROUGE = colors.HexColor('#B03A26')

MARGE = 15 * mm


def montant(valeur):
    """
    Formate un montant comme à l'écran, en réutilisant le filtre |euros.

    L'espace fine insécable (U+202F) que pose ce filtre n'existe pas dans
    WinAnsiEncoding, le jeu de caractères des polices intégrées de ReportLab :
    elle s'imprimerait « 12?345?€ ». On la remplace par l'espace insécable
    ordinaire (U+00A0), qui rend pareil et qui, elle, est encodable.
    """
    return euros(valeur).replace(' ', ' ')


def _styles():
    base = ParagraphStyle(
        'base', fontName='Helvetica', fontSize=9, leading=12, textColor=NOIR,
    )
    return {
        'titre': ParagraphStyle(
            'titre', parent=base, fontName='Helvetica-Bold', fontSize=17, leading=21,
        ),
        'garage': ParagraphStyle('garage', parent=base, fontSize=9, textColor=GRIS),
        'periode': ParagraphStyle(
            'periode', parent=base, fontName='Helvetica-Bold', fontSize=10.5, leading=14,
        ),
        'edition': ParagraphStyle(
            'edition', parent=base, fontSize=8.5, textColor=GRIS, alignment=TA_RIGHT,
        ),
        'section': ParagraphStyle(
            'section', parent=base, fontName='Helvetica-Bold', fontSize=8,
            textColor=GRIS, spaceAfter=6,
        ),
        'kpi_label': ParagraphStyle(
            'kpi_label', parent=base, fontSize=7.5, leading=10, textColor=GRIS,
        ),
        'kpi_valeur': ParagraphStyle(
            'kpi_valeur', parent=base, fontName='Helvetica-Bold', fontSize=14, leading=18,
        ),
        'cellule': base,
        'vide': ParagraphStyle('vide', parent=base, textColor=GRIS),
    }


def _entete(garage, libelle_periode, edite_le, s):
    """Bloc d'identification, en haut de la première page."""
    adresse = ' · '.join(
        m for m in [garage.adresse, f'{garage.code_postal} {garage.ville}'.strip()] if m
    ) if garage else ''

    gauche = [Paragraph('Synthèse des ventes', s['titre'])]
    if garage:
        gauche.append(Spacer(1, 3))
        gauche.append(Paragraph(garage.nom, s['garage']))
        if adresse:
            gauche.append(Paragraph(adresse, s['garage']))

    tableau = Table(
        [[gauche, Paragraph(f"Édité le {edite_le:%d/%m/%Y}", s['edition'])]],
        colWidths=[110 * mm, None],
    )
    tableau.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    return [
        tableau,
        Spacer(1, 10),
        Paragraph(libelle_periode, s['periode']),
        Spacer(1, 14),
    ]


def _tableau_ventes(donnees, s, largeur):
    """Le détail vente par vente, avec sa ligne de total."""
    entetes = ['Date', 'Véhicule', "Prix d'achat", 'Frais', 'Prix de vente', 'Marge']
    lignes = [entetes]

    for v in donnees['ventes']:
        lignes.append([
            f'{v.date_vente:%d/%m/%Y}',
            # Un Paragraph plutôt qu'une chaîne : un nom long revient à la
            # ligne dans la cellule au lieu de déborder sur la colonne voisine.
            Paragraph(f'{v.marque} {v.modele}', s['cellule']),
            montant(v.prix_achat_calc),
            montant(v.frais_reel_calc),
            montant(v.prix_vente),
            montant(v.marge_interne_calc),
        ])

    totaux = donnees['totaux']
    lignes.append([
        '', 'Total',
        montant(totaux['prix_achat']), montant(totaux['frais']),
        montant(totaux['prix_vente']), montant(totaux['marge']),
    ])

    colonnes = [20 * mm, None, 26 * mm, 22 * mm, 27 * mm, 26 * mm]
    colonnes[1] = largeur - sum(c for c in colonnes if c)

    tableau = Table(lignes, colWidths=colonnes, repeatRows=1)

    style = [
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('TEXTCOLOR', (0, 0), (-1, -1), NOIR),
        ('BACKGROUND', (0, 0), (-1, 0), GRIS_FOND),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, GRIS_CLAIR),
        # Ligne de total : filet plus marqué au-dessus et gras.
        ('LINEABOVE', (0, -1), (-1, -1), 0.9, NOIR),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TOPPADDING', (0, -1), (-1, -1), 7),
    ]

    # Une marge négative en rouge. Reste identifiable en niveaux de gris :
    # le signe « - » la porte déjà.
    for i, v in enumerate(donnees['ventes'], start=1):
        if (v.marge_interne_calc or 0) < 0:
            style.append(('TEXTCOLOR', (5, i), (5, i), ROUGE))
    if donnees['totaux']['marge'] < 0:
        style.append(('TEXTCOLOR', (5, -1), (5, -1), ROUGE))

    tableau.setStyle(TableStyle(style))
    return tableau


ECART_CARTES = 6


def _indicateurs(donnees, s, largeur):
    """
    Les quatre chiffres de pilotage, en cartes sur le même gris que
    l'en-tête du tableau.

    ReportLab ne sait pas espacer deux cellules voisines : on intercale
    donc des colonnes vides et étroites, laissées sans fond, qui font
    office de gouttière entre les cartes.
    """
    cases = [
        ('Véhicules vendus', str(donnees['nb_vendus'])),
        ('Véhicules achetés', str(donnees['nb_achetes'])),
        ('Marge réalisée', montant(donnees['marge'])),
        ('En stock à ce jour', str(donnees['nb_stock'])),
    ]

    largeur_carte = (largeur - 3 * ECART_CARTES) / 4

    ligne, colonnes, colonnes_cartes = [], [], []
    for index, (label, valeur) in enumerate(cases):
        if index:
            ligne.append('')
            colonnes.append(ECART_CARTES)
        colonnes_cartes.append(len(ligne))
        ligne.append([
            Paragraph(label, s['kpi_label']),
            Paragraph(valeur, s['kpi_valeur']),
        ])
        colonnes.append(largeur_carte)

    tableau = Table([ligne], colWidths=colonnes)

    style = [
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]
    for col in colonnes_cartes:
        style.extend([
            ('BACKGROUND', (col, 0), (col, 0), GRIS_FOND),
            ('LEFTPADDING', (col, 0), (col, 0), 10),
            ('RIGHTPADDING', (col, 0), (col, 0), 10),
            ('TOPPADDING', (col, 0), (col, 0), 9),
            ('BOTTOMPADDING', (col, 0), (col, 0), 10),
        ])

    tableau.setStyle(TableStyle(style))
    return tableau


def _pied_de_page(canevas, doc):
    """Numéro de page, répété en bas de chaque page."""
    canevas.saveState()
    canevas.setFont('Helvetica', 8)
    canevas.setFillColor(GRIS)
    canevas.drawRightString(
        A4[0] - MARGE, MARGE - 6 * mm, f'Page {canevas.getPageNumber()}',
    )
    canevas.restoreState()


def rendre_synthese_pdf(garage, libelle_periode, donnees, edite_le):
    """Rend la synthèse et renvoie les octets du PDF."""
    tampon = io.BytesIO()
    titre = f"Synthèse des ventes · {garage.nom}" if garage else 'Synthèse des ventes'

    doc = SimpleDocTemplate(
        tampon, pagesize=A4,
        leftMargin=MARGE, rightMargin=MARGE,
        topMargin=MARGE, bottomMargin=MARGE,
        title=titre, author=garage.nom if garage else '',
    )

    s = _styles()
    largeur = doc.width
    elements = _entete(garage, libelle_periode, edite_le, s)

    if donnees['ventes']:
        elements.append(_tableau_ventes(donnees, s, largeur))
    else:
        elements.append(Paragraph('Aucune vente sur cette période.', s['vide']))

    elements.append(Spacer(1, 18))
    # KeepTogether : le bloc d'indicateurs ne se coupe pas entre son titre et
    # ses chiffres si la page se termine juste là.
    elements.append(KeepTogether([
        Paragraph("SUR LA PÉRIODE", s['section']),
        _indicateurs(donnees, s, largeur),
    ]))

    doc.build(elements, onFirstPage=_pied_de_page, onLaterPages=_pied_de_page)
    return tampon.getvalue()
