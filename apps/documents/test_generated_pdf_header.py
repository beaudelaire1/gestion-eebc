"""L'entête des PDF générés doit se répéter comme le pied de page.

Le pied était déclaré ``position: running(page-footer)`` et tiré dans
``@bottom-left`` : il apparaissait sur chaque feuille. L'entête, qui porte le
logo, le nom de l'église, sa devise et ses coordonnées, restait dans le flux du
document : sur une convocation de deux pages, la deuxième arrivait sans aucune
identité, ni le moindre élément de la charte.

Ces tests passent par l'arbre de rendu de WeasyPrint plutôt que par le PDF
final : c'est là que se lisent la présence par page et la géométrie.
"""

from datetime import date
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

from apps.documents.generation import build_generated_document_context
from apps.documents.models import GeneratedDocument

pytestmark = pytest.mark.django_db

PX_PER_CM = 96 / 2.54
TOP_MARGIN_CM = 5.3

# Assez de contenu pour forcer une seconde page : c'est le seul cas où le
# défaut se voyait.
LONG_BODY = ''.join(
    f'<p>Paragraphe {i} de la convocation, destiné à remplir la page.</p>'
    for i in range(1, 45)
)


def _classes(box):
    element = getattr(box, 'element', None)
    if element is None:
        return set()
    return set((element.get('class') or '').split())


def _find(box, class_name, found=None):
    found = [] if found is None else found
    if class_name in _classes(box):
        found.append(box)
    for child in getattr(box, 'children', ()) or ():
        _find(child, class_name, found)
    return found


def _render_pages(kind, body_html=LONG_BODY):
    from weasyprint import HTML

    logo = Path(settings.BASE_DIR) / 'static' / 'images' / 'eebc-logo.png'
    doc = GeneratedDocument(
        title="Convocation à l'assemblée générale",
        kind=kind,
        reference='CONV-2026-001',
        document_date=date(2026, 9, 3),
        recipient_name='Monsieur Dupont',
        body_html=body_html,
    )
    html = render_to_string(
        'documents/generated/pdf_template.html',
        build_generated_document_context(
            doc, logo_path=logo.as_uri() if logo.exists() else ''
        ),
    )
    return HTML(string=html, base_url=str(settings.BASE_DIR)).render().pages


def test_header_repeats_on_every_page_like_the_footer():
    pages = _render_pages('convocation')

    assert len(pages) > 1, 'le corps doit tenir sur plusieurs pages'
    for number, page in enumerate(pages, start=1):
        headers = _find(page._page_box, 'page-header')
        footers = _find(page._page_box, 'page-footer')
        assert headers, f"page {number} sans entête"
        assert footers, f"page {number} sans pied"


def test_header_is_not_clipped_by_the_page_edge():
    """L'entête tirée dans @top-center débordait par le haut de la feuille."""
    pages = _render_pages('convocation')
    budget = TOP_MARGIN_CM * PX_PER_CM

    for number, page in enumerate(pages, start=1):
        header = _find(page._page_box, 'page-header')[0]
        assert header.position_y >= 0, (
            f"page {number} : entête à y={header.position_y:.1f}, "
            'donc rognée au-dessus du bord de page'
        )
        assert header.position_y + header.height <= budget + 1, (
            f"page {number} : entête haute de {header.height:.1f}px à "
            f"y={header.position_y:.1f}, elle mord sur le corps du texte"
        )


@pytest.mark.parametrize('kind', ['convocation', 'attestation', 'note_service'])
def test_every_kind_keeps_its_header_within_the_margin(kind):
    """Chaque type a son propre habillage d'entête, donc sa propre hauteur."""
    pages = _render_pages(kind)
    budget = TOP_MARGIN_CM * PX_PER_CM

    for page in pages:
        header = _find(page._page_box, 'page-header')[0]
        assert 0 <= header.position_y
        assert header.position_y + header.height <= budget + 1


def test_classification_card_stays_on_the_first_page():
    """La fiche de classification décrit le document, elle n'est pas un entête."""
    pages = _render_pages('convocation')

    assert _find(pages[0]._page_box, 'page-header__side')
    for page in pages[1:]:
        assert not _find(page._page_box, 'page-header__side')


def test_header_carries_the_church_identity():
    pages = _render_pages('convocation')

    texts = []

    def collect(box):
        text = getattr(box, 'text', None)
        if text:
            texts.append(text)
        for child in getattr(box, 'children', ()) or ():
            collect(child)

    # Sur la dernière page, donc hors du premier écran : c'est ce qui manquait.
    collect(_find(pages[-1]._page_box, 'page-header')[0])
    blob = ' '.join(texts)

    assert 'glise' in blob, 'le nom de l\'église doit figurer dans l\'entête'
