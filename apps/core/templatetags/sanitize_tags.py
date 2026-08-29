"""Filtres template pour la sanitisation de contenu HTML."""
from urllib.parse import urlparse

import nh3
from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Tags HTML autorisés pour le contenu CMS
ALLOWED_TAGS = {
    'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'div', 'em',
    'figcaption', 'figure', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr',
    'i', 'iframe', 'img', 'li', 'mark', 'ol', 'p', 'pre', 'source',
    'span', 'strong', 'table', 'tbody', 'td', 'th', 'thead', 'tr',
    'u', 'ul', 'video',
}

ALLOWED_ATTRIBUTES = {
    '*': {'class', 'style'},
    'a': {'href', 'title', 'target'},
    'iframe': {
        'allow', 'allowfullscreen', 'frameborder', 'height', 'loading',
        'referrerpolicy', 'src', 'title', 'width',
    },
    'img': {'src', 'alt', 'width', 'height'},
    'source': {'src', 'type'},
    'video': {
        'controls', 'height', 'loop', 'muted', 'playsinline', 'poster',
        'preload', 'src', 'width',
    },
}

VIDEO_IFRAME_SOURCES = {
    'www.youtube.com': ('/embed/',),
    'youtube.com': ('/embed/',),
    'www.youtube-nocookie.com': ('/embed/',),
    'youtube-nocookie.com': ('/embed/',),
    'player.vimeo.com': ('/video/',),
    'www.dailymotion.com': ('/embed/video/',),
    'geo.dailymotion.com': ('/player.html',),
    'www.facebook.com': ('/plugins/video.php',),
    'web.facebook.com': ('/plugins/video.php',),
}


def _is_allowed_video_iframe(src):
    parsed = urlparse(src or '')
    hostname = (parsed.hostname or '').lower()
    allowed_paths = VIDEO_IFRAME_SOURCES.get(hostname)
    if parsed.scheme != 'https' or not allowed_paths:
        return False
    return any((parsed.path or '').startswith(path) for path in allowed_paths)


def _clean_video_embeds(html):
    soup = BeautifulSoup(html, 'html.parser')

    for iframe in soup.find_all('iframe'):
        if not _is_allowed_video_iframe(iframe.get('src')):
            iframe.decompose()
            continue
        iframe['loading'] = 'lazy'
        iframe['referrerpolicy'] = 'strict-origin-when-cross-origin'
        iframe['allowfullscreen'] = ''
        if not iframe.get('title'):
            iframe['title'] = 'Video integree'

    for video in soup.find_all('video'):
        video['controls'] = ''
        if not video.get('preload'):
            video['preload'] = 'metadata'

    return str(soup)


@register.filter(name='sanitize', is_safe=True)
def sanitize_html(value):
    """Nettoie le HTML en ne gardant que les tags/attributs autorisés."""
    if not value:
        return ''
    cleaned = nh3.clean(
        str(value),
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        link_rel='noopener noreferrer',
    )
    return mark_safe(_clean_video_embeds(cleaned))
