"""
Template tags pour les formulaires avec gestion des erreurs.
"""

from django import template
from django.forms.widgets import CheckboxInput, RadioSelect

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Récupère un élément d'un dictionnaire ou d'un objet par clé."""
    if hasattr(dictionary, key):
        return getattr(dictionary, key)
    elif hasattr(dictionary, '__getitem__'):
        try:
            return dictionary[key]
        except (KeyError, TypeError):
            return None
    return None


@register.filter
def split(value, delimiter=','):
    """Divise une chaîne par un délimiteur."""
    return value.split(delimiter)


@register.filter
def div(value, divisor):
    """Division simple pour les templates."""
    try:
        return int(value) // int(divisor)
    except (ValueError, ZeroDivisionError):
        return 1


@register.filter
def is_checkbox(field):
    """Vérifie si un champ est une checkbox."""
    return isinstance(field.field.widget, CheckboxInput)


@register.filter
def is_radio(field):
    """Vérifie si un champ est un radio button."""
    return isinstance(field.field.widget, RadioSelect)


@register.filter
def add_class(field, css_class):
    """Ajoute une classe CSS à un champ de formulaire."""
    existing_classes = field.field.widget.attrs.get('class', '')
    new_classes = f"{existing_classes} {css_class}".strip()
    return field.as_widget(attrs={'class': new_classes})


@register.filter
def add_error_class(field):
    """Ajoute la classe d'erreur Bootstrap si le champ a des erreurs."""
    if field.errors:
        return add_class(field, 'is-invalid')
    elif field.value():
        return add_class(field, 'is-valid')
    return field


@register.inclusion_tag('components/form_field.html')
def render_field(field, show_label=True, show_help=True):
    """Rend un champ de formulaire avec gestion des erreurs."""
    return {
        'field': field,
        'show_label': show_label,
        'show_help': show_help,
    }


@register.inclusion_tag('components/form_field_inline.html')
def render_checkbox(field):
    """Rend un champ checkbox avec gestion des erreurs."""
    return {'field': field}


@register.inclusion_tag('components/form_errors.html')
def render_form_errors(form):
    """Rend les erreurs globales du formulaire."""
    return {'form': form}


@register.simple_tag
def field_has_errors(form, field_name):
    """Vérifie si un champ spécifique a des erreurs."""
    if hasattr(form, field_name):
        field = getattr(form, field_name)
        return bool(field.errors)
    return False


@register.simple_tag
def form_has_errors(form):
    """Vérifie si le formulaire a des erreurs."""
    return bool(form.errors)


@register.filter
def field_type(field):
    """Retourne le type de widget d'un champ."""
    return field.field.widget.__class__.__name__


@register.filter
def placeholder(field, text):
    """Ajoute un placeholder à un champ."""
    field.field.widget.attrs['placeholder'] = text
    return field