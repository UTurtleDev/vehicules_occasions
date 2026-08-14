from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

ESPACE_FINE = ' '   # espace fine insécable : 12 345 € ne se coupe pas en fin de ligne


@register.filter
def euros(valeur, decimales=0):
    """Formate un montant à la française : 12 345 € / -1 250,50 €."""
    if valeur is None or valeur == '':
        return '—'
    try:
        montant = Decimal(valeur)
    except (InvalidOperation, TypeError, ValueError):
        return '—'

    entier, _, decimale = f'{montant:,.{decimales}f}'.partition('.')
    entier = entier.replace(',', ESPACE_FINE)
    return f'{entier},{decimale}{ESPACE_FINE}€' if decimale else f'{entier}{ESPACE_FINE}€'


@register.simple_tag
def toggle_qs(request, key, value):
    params = request.GET.copy()
    value = str(value)
    values = params.getlist(key)
    if value in values:
        values.remove(value)
    else:
        values.append(value)
    params.setlist(key, values)
    params.pop('page', None)
    encoded = params.urlencode()
    return '?' + encoded if encoded else '?'


@register.simple_tag
def set_qs(request, key, value):
    params = request.GET.copy()
    if value in (None, ''):
        params.pop(key, None)
    else:
        params[key] = value
    params.pop('page', None)
    encoded = params.urlencode()
    return '?' + encoded if encoded else '?'


@register.simple_tag
def page_qs(request, page):
    params = request.GET.copy()
    params['page'] = page
    return '?' + params.urlencode()


@register.simple_tag
def is_active(request, key, value):
    return str(value) in request.GET.getlist(key)
