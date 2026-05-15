from datetime import date

import pytest
from bs4 import BeautifulSoup
from django.template.loader import render_to_string
from django.urls import reverse


@pytest.mark.django_db
class TestGeneratedDocumentsPremium:

    def test_preview_uses_kind_specific_sober_branding(self, authenticated_client, admin_user):
        from apps.documents.models import GeneratedDocument

        doc = GeneratedDocument.objects.create(
            title='Réunion du conseil élargi',
            kind=GeneratedDocument.Kind.COMPTE_RENDU,
            reference='EEBC/CR/2026/007',
            document_date=date(2026, 4, 18),
            subject='Synthèse trimestrielle',
            body_html='<p>Contenu de validation.</p>',
            signature_name='Jean Exemple',
            signature_title='Secrétaire administratif',
            created_by=admin_user,
        )

        response = authenticated_client.get(reverse('documents:generated_preview', args=[doc.pk]))

        assert response.status_code == 200
        content = response.content.decode()
        assert 'Compte rendu' in content
        assert 'Séance concernée' in content
        assert 'Mémoire de séance' in content
        assert 'document-page--meeting-minutes' in content
        assert 'premium' not in content.lower()
        assert 'institutionnel' not in content.lower()

    def test_generated_pdf_links_keep_mobile_session_context(self, authenticated_client, admin_user):
        from apps.documents.models import GeneratedDocument

        doc = GeneratedDocument.objects.create(
            title='Courrier mobile',
            kind=GeneratedDocument.Kind.COURRIER,
            document_date=date(2026, 4, 18),
            body_html='<p>Contenu PDF.</p>',
            created_by=admin_user,
        )

        pdf_url = reverse('documents:generated_pdf', args=[doc.pk])
        checked_pages = [
            reverse('documents:generated_preview', args=[doc.pk]),
            reverse('documents:generated_edit', args=[doc.pk]),
            reverse('documents:generated_list'),
        ]

        for page_url in checked_pages:
            response = authenticated_client.get(page_url)
            assert response.status_code == 200

            soup = BeautifulSoup(response.content.decode(), 'html.parser')
            links = soup.find_all('a', href=pdf_url)
            assert links, f"Lien PDF absent de {page_url}"
            assert all(link.get('target') != '_blank' for link in links)

    def test_document_kinds_expose_distinct_visual_variants(self, authenticated_client, admin_user):
        from apps.documents.generation import build_generated_document_context
        from apps.documents.models import GeneratedDocument

        convocation = GeneratedDocument.objects.create(
            title='Réunion stratégique',
            kind=GeneratedDocument.Kind.CONVOCATION,
            reference='EEBC/CNV/2026/004',
            document_date=date(2026, 4, 18),
            subject='Validation du calendrier',
            body_html='<p>Présence requise.</p>',
            created_by=admin_user,
        )
        attestation = GeneratedDocument.objects.create(
            title='Attestation de présence',
            kind=GeneratedDocument.Kind.ATTESTATION,
            reference='EEBC/AT/2026/005',
            document_date=date(2026, 4, 18),
            subject='Session de formation',
            body_html='<p>Document établi pour servir et valoir ce que de droit.</p>',
            created_by=admin_user,
        )

        convocation_response = authenticated_client.get(reverse('documents:generated_preview', args=[convocation.pk]))
        attestation_response = authenticated_client.get(reverse('documents:generated_preview', args=[attestation.pk]))

        assert convocation_response.status_code == 200
        assert attestation_response.status_code == 200

        convocation_content = convocation_response.content.decode()
        attestation_content = attestation_response.content.decode()

        assert 'document-page--ceremonial-call' in convocation_content
        assert 'Avis de réunion' in convocation_content
        assert 'Séance convoquée' in convocation_content
        assert 'document-page--certificate' in attestation_content
        assert 'Document certifié' in attestation_content
        assert 'Nature de l' in attestation_content

        convocation_pdf_html = render_to_string(
            'documents/generated/pdf_template.html',
            build_generated_document_context(convocation),
        )
        attestation_pdf_html = render_to_string(
            'documents/generated/pdf_template.html',
            build_generated_document_context(attestation),
        )

        assert 'document-page--ceremonial-call' in convocation_pdf_html
        assert 'document-page--certificate' in attestation_pdf_html
        assert 'CONVOC' in convocation_pdf_html
        assert 'ATTESTE' in attestation_pdf_html

    def test_courrier_preview_avoids_marketing_labels_and_keeps_subject_inline(self, authenticated_client, admin_user):
        from apps.documents.models import GeneratedDocument

        doc = GeneratedDocument.objects.create(
            title='Courrier de suivi',
            kind=GeneratedDocument.Kind.COURRIER,
            reference='EEBC/COU/2026/001',
            document_date=date(2026, 4, 18),
            subject='Demande de vérification',
            body_html='<p>Contenu.</p>',
            created_by=admin_user,
        )

        response = authenticated_client.get(reverse('documents:generated_preview', args=[doc.pk]))

        assert response.status_code == 200
        content = response.content.decode()
        assert 'Courrier institutionnel' not in content
        assert 'Correspondance externe' not in content
        assert 'Mise en forme premium' not in content
        assert 'subject-banner__label' in content
        assert 'subject-banner__value' in content
        assert 'courrier-lead' in content
        assert 'hero-panel' not in content
        assert '<div class="brand-overline"></div>' not in content

    def test_template_endpoint_returns_richer_convocation_model(self, authenticated_client):
        response = authenticated_client.get(reverse('documents:generated_template'), {'kind': 'convocation'})

        assert response.status_code == 200
        payload = response.json()
        assert 'Convocation officielle' in payload['html']
        assert 'Ordre du jour' in payload['html']

    def test_pdf_generation_keeps_premium_template(self, admin_user):
        from apps.documents.generation import render_generated_document_pdf
        from apps.documents.models import GeneratedDocument

        doc = GeneratedDocument.objects.create(
            title='Attestation premium',
            kind=GeneratedDocument.Kind.ATTESTATION,
            reference='EEBC/AT/2026/003',
            document_date=date(2026, 4, 18),
            subject='Attestation de présence',
            body_html='<p>Nous certifions la présence régulière du bénéficiaire.</p>',
            signature_name='Pierre Lauriole',
            signature_title='Pasteur principal',
            created_by=admin_user,
        )

        pdf_bytes = render_generated_document_pdf(doc)

        assert pdf_bytes.startswith(b'%PDF')
        assert len(pdf_bytes) > 1000

    def test_preview_and_pdf_support_quill_alignment_and_page_guards(self, authenticated_client, admin_user):
        from apps.documents.generation import build_generated_document_context
        from apps.documents.models import GeneratedDocument

        doc = GeneratedDocument.objects.create(
            title='Rapport avec mise en page riche',
            kind=GeneratedDocument.Kind.RAPPORT,
            reference='EEBC/RP/2026/011',
            document_date=date(2026, 4, 18),
            subject='Synthèse longue',
            body_html='''<p class="ql-align-justify">Premier paragraphe long pour contrôler la justification.</p><p class="ql-align-right ql-indent-1">Bloc secondaire aligné à droite.</p>''',
            signature_name='Marie Exemple',
            signature_title='Chargée de rédaction',
            created_by=admin_user,
        )

        response = authenticated_client.get(reverse('documents:generated_preview', args=[doc.pk]))

        assert response.status_code == 200
        content = response.content.decode()
        for expected in ('.body .ql-align-justify', '.body .ql-indent-1'):
            assert expected in content

        pdf_html = render_to_string(
            'documents/generated/pdf_template.html',
            build_generated_document_context(doc),
        )

        for expected in ('.body .ql-align-justify', '.body .ql-indent-1', 'page-break-inside: avoid'):
            assert expected in pdf_html

    def test_form_sanitizes_pasted_styles_and_keeps_font_controls(self):
        from apps.documents.forms import GeneratedDocumentForm

        form = GeneratedDocumentForm(data={
            'title': 'Courrier nettoyé',
            'kind': 'courrier',
            'document_date': '2026-04-18',
            'visibility': 'staff',
            'body_html': '<p style="line-height: 2.4; color: white; font-family: Cambria; font-size: 18pt;">Texte visible</p><p><br></p><p><br></p><p style="opacity: 0; font-size: 0pt;">Texte caché</p>',
        })

        assert form.is_valid(), form.errors
        cleaned_html = form.cleaned_data['body_html']
        assert 'line-height' not in cleaned_html
        assert 'color:' not in cleaned_html
        assert 'opacity:' not in cleaned_html
        assert 'font-family: Cambria' in cleaned_html
        assert 'font-size: 18pt' in cleaned_html
        assert cleaned_html.count('<p><br/></p>') <= 1

    def test_preview_renders_cleaned_rich_text_for_existing_document(self, authenticated_client, admin_user):
        from apps.documents.models import GeneratedDocument

        doc = GeneratedDocument.objects.create(
            title='Courrier avec styles collés',
            kind=GeneratedDocument.Kind.COURRIER,
            reference='EEBC/COU/2026/012',
            document_date=date(2026, 4, 18),
            body_html='<p style="line-height: 3; color: white; font-family: Cambria; font-size: 18pt;">Texte rétabli</p>',
            created_by=admin_user,
        )

        response = authenticated_client.get(reverse('documents:generated_preview', args=[doc.pk]))

        assert response.status_code == 200
        content = response.content.decode()
        assert 'font-family: Cambria' in content
        assert 'font-size: 18pt' in content
        assert 'line-height: 3' not in content
        assert 'color: white' not in content