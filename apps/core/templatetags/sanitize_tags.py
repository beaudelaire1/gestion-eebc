"""Filtres template pour la sanitisation de contenu HTML."""
import nh3
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Tags HTML autorisés pour le contenu CMS
ALLOWED_TAGS = {
    'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'div', 'em',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
    'li', 'mark', 'ol', 'p', 'pre', 'span', 'strong', 'table', 'tbody',
    'td', 'th', 'thead', 'tr', 'u', 'ul',
}

ALLOWED_ATTRIBUTES = {
    '*': {'class', 'style'},
    'a': {'href', 'title', 'target'},
    'img': {'src', 'alt', 'width', 'height'},
}


@register.filter(name='sanitize', is_safe=True)
def sanitize_html(value):
    """Nettoie le HTML en ne gardant que les tags/attributs autorisés."""
    if not value:
        return ''
    return mark_safe(nh3.clean(
        str(value),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        link_rel='noopener noreferrer',
    ))
