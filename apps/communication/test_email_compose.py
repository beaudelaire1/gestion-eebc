"""Tests de l'éditeur d'e-mails intégré (composition + envoi par département)."""
import pytest
from django.core import mail
from django.urls import reverse

from apps.communication.models import EmailLog, EmailSenderDepartment
from test_factories import UserFactory


@pytest.fixture
def department(db):
    return EmailSenderDepartment.objects.get(name='Secrétariat')


@pytest.fixture
def comm_admin(db):
    return UserFactory(role='secretariat', email='admin@eglise-ebc.org')


@pytest.fixture
def team_recipient(db):
    return UserFactory(role='diacre', email='diacre@eglise-ebc.org')


@pytest.mark.django_db
class TestEmailCompose:
    
    def test_acces_refuse_membre_lambda(self, client):
        member = UserFactory(role='membre')
        client.force_login(member)
        response = client.get(reverse('communication:email_compose'))
        # La composition d'e-mails est hors du périmètre libre-service :
        # OrdinaryMemberAccessMiddleware la refuse avant la vue.
        assert response.status_code == 403
    
    def test_acces_autorise_secretariat(self, client, comm_admin):
        client.force_login(comm_admin)
        response = client.get(reverse('communication:email_compose'))
        assert response.status_code == 200
        assert 'form' in response.context
    
    def test_membre_lambda_exclu_des_destinataires(self, client, comm_admin, team_recipient):
        lambda_member = UserFactory(role='membre', email='lambda@example.com')
        client.force_login(comm_admin)
        response = client.get(reverse('communication:email_compose'))
        recipients_qs = response.context['form'].fields['recipients'].queryset
        assert team_recipient in recipients_qs
        assert lambda_member not in recipients_qs
    
    def test_envoi_email_avec_signature_departement(self, client, comm_admin, department, team_recipient):
        client.force_login(comm_admin)
        response = client.post(reverse('communication:email_compose'), {
            'department': department.pk,
            'recipients': [team_recipient.pk],
            'subject': 'Réunion des équipes',
            'body': '<p>Bonjour, la réunion est confirmée pour dimanche.</p>',
        })
        assert response.status_code == 302
        assert len(mail.outbox) == 1
        sent = mail.outbox[0]
        assert sent.from_email == '"Secrétariat — EEBC" <secretariat@eglise-ebc.org>'
        assert sent.to == ['diacre@eglise-ebc.org']
        # Fallback texte brut + alternative HTML
        assert 'la réunion est confirmée' in sent.body
        html_body = sent.alternatives[0][0]
        assert 'Secrétariat' in html_body
        assert '+594 694 47 28 06' in html_body
        assert 'secretariat@eglise-ebc.org' in html_body
        # Log créé
        log = EmailLog.objects.get(recipient_email='diacre@eglise-ebc.org')
        assert log.status == EmailLog.Status.SENT
    
    def test_html_dangereux_sanitise(self, client, comm_admin, department, team_recipient):
        client.force_login(comm_admin)
        client.post(reverse('communication:email_compose'), {
            'department': department.pk,
            'recipients': [team_recipient.pk],
            'subject': 'Test sécurité',
            'body': '<p>Message légitime de test</p><script>alert("xss")</script>',
        })
        html_body = mail.outbox[0].alternatives[0][0]
        assert '<script>' not in html_body
        assert 'Message légitime' in html_body
    
    def test_formulaire_invalide_sans_envoi(self, client, comm_admin, department):
        client.force_login(comm_admin)
        response = client.post(reverse('communication:email_compose'), {
            'department': department.pk,
            'recipients': [],
            'subject': 'X',
            'body': '<p>court</p>',
        })
        assert response.status_code == 200
        assert response.context['form'].errors
        assert len(mail.outbox) == 0
    
    def test_envoi_adresse_externe(self, client, comm_admin, department):
        """On peut écrire à une adresse externe (ex: mairie) sans compte."""
        client.force_login(comm_admin)
        response = client.post(reverse('communication:email_compose'), {
            'department': department.pk,
            'recipients': [],
            'external_recipients': 'mairie@ville-cayenne.fr, partenaire@example.org',
            'subject': 'Demande de salle municipale',
            'body': '<p>Madame, Monsieur, nous sollicitons la salle polyvalente.</p>',
        })
        assert response.status_code == 302
        assert len(mail.outbox) == 2
        destinataires = {m.to[0] for m in mail.outbox}
        assert destinataires == {'mairie@ville-cayenne.fr', 'partenaire@example.org'}

    def test_dedoublonne_destinataire_interne_et_externe_identiques(self, client, comm_admin, department, team_recipient):
        """Même email saisi en interne + externe => un seul envoi effectif."""
        client.force_login(comm_admin)
        response = client.post(reverse('communication:email_compose'), {
            'department': department.pk,
            'recipients': [team_recipient.pk],
            'external_recipients': team_recipient.email,
            'subject': 'Message unique',
            'body': '<p>Ce message doit partir une seule fois.</p>',
        })

        assert response.status_code == 302
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [team_recipient.email]
        assert EmailLog.objects.filter(recipient_email=team_recipient.email).count() == 1
    
    def test_adresse_externe_invalide_rejetee(self, client, comm_admin, department):
        client.force_login(comm_admin)
        response = client.post(reverse('communication:email_compose'), {
            'department': department.pk,
            'external_recipients': 'pas-une-adresse',
            'subject': 'Test',
            'body': '<p>Message de test suffisant.</p>',
        })
        assert response.status_code == 200
        assert 'external_recipients' in response.context['form'].errors
        assert len(mail.outbox) == 0
    
    def test_envoi_avec_piece_jointe(self, client, comm_admin, department, team_recipient):
        from django.core.files.uploadedfile import SimpleUploadedFile
        client.force_login(comm_admin)
        pdf = SimpleUploadedFile('courrier.pdf', b'%PDF-1.4 contenu test', content_type='application/pdf')
        response = client.post(reverse('communication:email_compose'), {
            'department': department.pk,
            'recipients': [team_recipient.pk],
            'subject': 'Courrier officiel',
            'body': '<p>Veuillez trouver le courrier en pièce jointe.</p>',
            'attachments': [pdf],
        })
        assert response.status_code == 302
        assert len(mail.outbox) == 1
        attachments = mail.outbox[0].attachments
        assert len(attachments) == 1
        assert attachments[0][0] == 'courrier.pdf'
        assert attachments[0][2] == 'application/pdf'
    
    def test_piece_jointe_extension_interdite(self, client, comm_admin, department, team_recipient):
        from django.core.files.uploadedfile import SimpleUploadedFile
        client.force_login(comm_admin)
        exe = SimpleUploadedFile('virus.exe', b'MZ', content_type='application/octet-stream')
        response = client.post(reverse('communication:email_compose'), {
            'department': department.pk,
            'recipients': [team_recipient.pk],
            'subject': 'Test sécurité fichier',
            'body': '<p>Message de test suffisant.</p>',
            'attachments': [exe],
        })
        assert response.status_code == 200
        assert 'attachments' in response.context['form'].errors
        assert len(mail.outbox) == 0
    
    def test_gabarit_charte_eebc(self, client, comm_admin, department, team_recipient):
        """Le gabarit premium contient l'identité EEBC complète."""
        client.force_login(comm_admin)
        client.post(reverse('communication:email_compose'), {
            'department': department.pk,
            'recipients': [team_recipient.pk],
            'subject': 'Invitation officielle',
            'body': '<p>Vous êtes cordialement invités.</p>',
        })
        html_body = mail.outbox[0].alternatives[0][0]
        assert 'Église Évangélique Baptiste' in html_body
        assert '#0A36FF' in html_body  # bleu charte
        assert '#f0c850' in html_body  # or charte
        assert 'Invitation officielle' in html_body
        assert '11 lot Calimbé 2' in html_body


@pytest.mark.django_db
class TestDepartmentSmtpMailbox:
    """Chaque département dispose d'une vraie boîte SMTP dédiée."""
    
    def test_nom_variable_environnement(self, department):
        assert department.smtp_password_env_name == 'EMAIL_PASSWORD_SECRETARIAT'
        assert department.smtp_password_legacy_env_name == 'EMAIL_BACKEND_SECRETARIAT'
    
    def test_connexion_dediee_si_mot_de_passe_configure(self, department, monkeypatch):
        monkeypatch.setenv('EMAIL_PASSWORD_SECRETARIAT', 'mot-de-passe-test')
        connection = department.get_smtp_connection()
        assert connection is not None
    
    def test_fallback_sans_mot_de_passe(self, department, monkeypatch):
        monkeypatch.delenv('EMAIL_PASSWORD_SECRETARIAT', raising=False)
        monkeypatch.delenv('EMAIL_BACKEND_SECRETARIAT', raising=False)
        assert department.get_smtp_connection() is None

    def test_alias_legacy_email_backend(self, department, monkeypatch):
        monkeypatch.delenv('EMAIL_PASSWORD_SECRETARIAT', raising=False)
        monkeypatch.setenv('EMAIL_BACKEND_SECRETARIAT', 'mot-de-passe-test-legacy')
        connection = department.get_smtp_connection()
        assert connection is not None
