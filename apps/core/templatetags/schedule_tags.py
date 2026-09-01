"""Filtres template pour l'affichage des horaires de culte."""

from django import template

register = template.Library()

# Icônes Bootstrap associées aux mots-clés d'activités courantes
_ICON_KEYWORDS = (
    ('culte', 'bi-sun'),
    ('étude', 'bi-book-half'),
    ('etude', 'bi-book-half'),
    ('biblique', 'bi-book-half'),
    ('prière', 'bi-moon-stars'),
    ('priere', 'bi-moon-stars'),
    ('jeune', 'bi-people-fill'),
    ('club', 'bi-mortarboard-fill'),
    ('chorale', 'bi-music-note-beamed'),
    ('louange', 'bi-music-note-beamed'),
    ('chant', 'bi-music-note-beamed'),
    ('école', 'bi-backpack'),
    ('ecole', 'bi-backpack'),
)


@register.filter
def parse_schedule(value):
    """Découpe un texte d'horaires libre en lignes structurées.

    Chaque ligne « Label : détail » devient ``{'label': ..., 'detail': ...}`` ;
    une ligne sans deux-points garde son texte dans ``label``.
    """
    items = []
    for line in str(value or '').splitlines():
        line = line.strip()
        if not line:
            continue
        label, sep, detail = line.partition(':')
        items.append({
            'label': label.strip(),
            'detail': detail.strip() if sep else '',
        })
    return items


@register.filter
def schedule_icon(label):
    """Retourne une classe d'icône Bootstrap adaptée au nom d'activité."""
    text = str(label or '').lower()
    for keyword, icon in _ICON_KEYWORDS:
        if keyword in text:
            return icon
    return 'bi-calendar-event'
