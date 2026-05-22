import pytest

from apps.core.templatetags.sanitize_tags import sanitize_html


pytestmark = pytest.mark.django_db


def test_sanitize_allows_trusted_video_iframe():
    html = """
    <p>Message</p>
    <iframe src="https://www.youtube.com/embed/abc123" width="560" height="315"></iframe>
    """

    rendered = str(sanitize_html(html))

    assert '<iframe' in rendered
    assert 'https://www.youtube.com/embed/abc123' in rendered
    assert 'loading="lazy"' in rendered
    assert 'referrerpolicy="strict-origin-when-cross-origin"' in rendered


def test_sanitize_removes_untrusted_iframe():
    html = '<iframe src="https://example.com/widget"></iframe><p>Texte conserve</p>'

    rendered = str(sanitize_html(html))

    assert '<iframe' not in rendered
    assert 'example.com/widget' not in rendered
    assert 'Texte conserve' in rendered


def test_sanitize_keeps_html5_video_source():
    html = """
    <video poster="https://example.com/poster.jpg">
        <source src="https://example.com/video.mp4" type="video/mp4">
    </video>
    """

    rendered = str(sanitize_html(html))

    assert '<video' in rendered
    assert '<source' in rendered
    assert 'https://example.com/video.mp4' in rendered
    assert 'controls' in rendered
    assert 'preload="metadata"' in rendered