"""Security validation for untrusted document uploads."""
from __future__ import annotations

from django.core.exceptions import ValidationError


ACTIVE_EXTENSIONS = {'svg', 'svgz', 'html', 'htm', 'xhtml', 'js', 'mjs'}


def file_extension(name: str) -> str:
    return (name.rsplit('.', 1)[-1].lower() if '.' in (name or '') else '')


def is_active_browser_document(name: str, content_type: str = '') -> bool:
    ext = file_extension(name)
    content_type = (content_type or '').split(';', 1)[0].strip().lower()
    return ext in ACTIVE_EXTENSIONS or content_type in {
        'image/svg+xml', 'text/html', 'application/xhtml+xml', 'application/javascript', 'text/javascript'
    }


def _read_head(uploaded_file, size=32):
    position = None
    try:
        if hasattr(uploaded_file, 'tell'):
            position = uploaded_file.tell()
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)
        head = uploaded_file.read(size)
        return bytes(head or b'')
    finally:
        if position is not None and hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(position)
        elif hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)


def validate_document_upload(uploaded_file):
    """Reject active browser documents and obvious extension/content mismatches.

    This is intentionally conservative. Office OpenXML/ODF/ZIP containers all
    use the ZIP signature and are still served as attachments outside previews.
    """
    name = uploaded_file.name or ''
    ext = file_extension(name)
    content_type = getattr(uploaded_file, 'content_type', '') or ''

    if is_active_browser_document(name, content_type):
        raise ValidationError('Les fichiers actifs de navigateur (SVG/HTML/JavaScript) ne sont pas autorisés.')

    head = _read_head(uploaded_file)
    signatures = {
        'pdf': lambda h: h.startswith(b'%PDF-'),
        'png': lambda h: h.startswith(b'\x89PNG\r\n\x1a\n'),
        'jpg': lambda h: h.startswith(b'\xff\xd8\xff'),
        'jpeg': lambda h: h.startswith(b'\xff\xd8\xff'),
        'gif': lambda h: h.startswith((b'GIF87a', b'GIF89a')),
        'webp': lambda h: len(h) >= 12 and h[:4] == b'RIFF' and h[8:12] == b'WEBP',
        'bmp': lambda h: h.startswith(b'BM'),
        'zip': lambda h: h.startswith((b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')),
        'docx': lambda h: h.startswith(b'PK'),
        'xlsx': lambda h: h.startswith(b'PK'),
        'pptx': lambda h: h.startswith(b'PK'),
        'odt': lambda h: h.startswith(b'PK'),
        'ods': lambda h: h.startswith(b'PK'),
        'doc': lambda h: h.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'),
        'xls': lambda h: h.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'),
        'ppt': lambda h: h.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'),
        'rtf': lambda h: h.lstrip().startswith(b'{\\rtf'),
    }
    checker = signatures.get(ext)
    if checker and not checker(head):
        raise ValidationError(f'Le contenu du fichier ne correspond pas au format .{ext}.')

    return uploaded_file
