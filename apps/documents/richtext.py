"""Utilitaires de normalisation du HTML riche pour les documents générés."""
from __future__ import annotations

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag


ALLOWED_INLINE_STYLES = {'font-family', 'font-size', 'text-align'}
ALLOWED_ALIGNMENT_VALUES = {'left', 'center', 'right', 'justify'}
ALLOWED_CLASS_PREFIXES = ('ql-align-', 'ql-indent-')
HIDDEN_FONT_SIZES = {'0', '0px', '0pt', '0rem', '0em', '1px'}


def _normalize_style_value(value: str) -> str:
    return ' '.join(value.replace('"', '').replace("'", '').split()).lower()


def _clean_inline_styles(style_value: str) -> str:
    cleaned_styles: list[str] = []
    for declaration in style_value.split(';'):
        if ':' not in declaration:
            continue
        name, value = declaration.split(':', 1)
        name = name.strip().lower()
        value = value.strip()
        normalized_value = _normalize_style_value(value)

        if not value or name not in ALLOWED_INLINE_STYLES:
            continue
        if name == 'text-align' and normalized_value not in ALLOWED_ALIGNMENT_VALUES:
            continue
        if name == 'font-size' and normalized_value in HIDDEN_FONT_SIZES:
            continue

        cleaned_styles.append(f'{name}: {value}')

    return '; '.join(cleaned_styles)


def _is_blank_paragraph(node: object) -> bool:
    if not isinstance(node, Tag) or node.name != 'p':
        return False
    if node.get_text(strip=True):
        return False

    significant_children = []
    for child in node.contents:
        if isinstance(child, NavigableString) and not child.strip():
            continue
        significant_children.append(child)

    return all(isinstance(child, Tag) and child.name == 'br' for child in significant_children)


def sanitize_generated_document_html(html: str) -> str:
    """Supprime les styles parasites du HTML Quill et limite les espacements anormaux."""
    soup = BeautifulSoup(html or '', 'html.parser')

    for node in soup.find_all(True):
        keep_classes = [
            class_name
            for class_name in node.get('class', [])
            if any(class_name.startswith(prefix) for prefix in ALLOWED_CLASS_PREFIXES)
        ]

        if keep_classes:
            node['class'] = keep_classes
        else:
            node.attrs.pop('class', None)

        for attr_name in list(node.attrs.keys()):
            if attr_name not in {'class', 'href', 'target', 'rel', 'style'}:
                del node.attrs[attr_name]

        if node.name != 'a':
            node.attrs.pop('href', None)
            node.attrs.pop('target', None)
            node.attrs.pop('rel', None)
        else:
            href = (node.get('href') or '').strip()
            if href and not href.startswith(('#', '/', 'http://', 'https://', 'mailto:', 'tel:')):
                node['href'] = '#'
            if node.get('target') == '_blank' and 'rel' not in node.attrs:
                node['rel'] = 'noopener noreferrer'

        if 'style' in node.attrs:
            cleaned_style = _clean_inline_styles(node['style'])
            if cleaned_style:
                node['style'] = cleaned_style
            else:
                del node.attrs['style']

    for span in soup.find_all('span'):
        if not span.attrs:
            span.unwrap()

    for child in list(soup.contents):
        if isinstance(child, NavigableString) and not child.strip():
            child.extract()

    previous_blank = False
    for child in list(soup.contents):
        if _is_blank_paragraph(child):
            if previous_blank:
                child.decompose()
                continue
            previous_blank = True
        else:
            previous_blank = False

    while soup.contents and isinstance(soup.contents[0], NavigableString) and not soup.contents[0].strip():
        soup.contents[0].extract()
    while soup.contents and isinstance(soup.contents[-1], NavigableString) and not soup.contents[-1].strip():
        soup.contents[-1].extract()
    while soup.contents and _is_blank_paragraph(soup.contents[0]):
        soup.contents[0].decompose()
    while soup.contents and _is_blank_paragraph(soup.contents[-1]):
        soup.contents[-1].decompose()

    return str(soup).strip()