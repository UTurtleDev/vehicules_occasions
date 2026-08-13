from django import template

register = template.Library()


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
