import uuid
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from .storage import document_storage


class DocumentCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom")
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon = models.CharField(max_length=50, default='bi-folder', verbose_name="Icône Bootstrap")
    color = models.CharField(max_length=7, default='#6c757d', verbose_name="Couleur")
    description = models.TextField(blank=True, verbose_name="Description")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Catégorie de document"
        verbose_name_plural = "Catégories de documents"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Document(models.Model):
    class MediaType(models.TextChoices):
        DOCUMENT = 'document', 'Document'
        IMAGE = 'image', 'Image'
        AUDIO = 'audio', 'Audio'
        VIDEO = 'video', 'Vidéo'

    class Source(models.TextChoices):
        MANUAL = 'manual', 'Import manuel'
        GENERATED = 'generated', 'Généré par le système'
        IMPORT = 'import', 'Import en masse'
        SCAN = 'scan', 'Numérisation'
        RECORDING = 'recording', 'Enregistrement'

    class Visibility(models.TextChoices):
        PRIVATE = 'private', 'Personnel (seulement moi et les admins)'
        STAFF = 'staff', 'Équipe (pasteurs, anciens, diacres, secrétariat, finance, encadrants)'
        ROLES = 'roles', 'Rôles spécifiques (à choisir ci-dessous)'
        PUBLIC = 'public', 'Tout le monde (tous les utilisateurs connectés)'

    # Rôles considérés comme faisant partie de « l'équipe »
    STAFF_ROLES = ('admin', 'secretariat', 'pasteur', 'ancien', 'diacre', 'finance', 'encadrant')

    title = models.CharField(max_length=255, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    file = models.FileField(upload_to='documents/%Y/%m/', storage=document_storage, verbose_name="Fichier")
    file_name = models.CharField(max_length=255, verbose_name="Nom du fichier")
    file_size = models.PositiveIntegerField(default=0, verbose_name="Taille (octets)")
    file_type = models.CharField(max_length=100, blank=True, verbose_name="Type MIME")
    media_type = models.CharField(
        max_length=10,
        choices=MediaType.choices,
        default=MediaType.DOCUMENT,
        verbose_name="Type de média",
    )
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name="Catégorie",
    )
    source = models.CharField(
        max_length=15,
        choices=Source.choices,
        default=Source.MANUAL,
        verbose_name="Source",
    )
    tags = models.CharField(max_length=500, blank=True, verbose_name="Tags (séparés par des virgules)")
    is_confidential = models.BooleanField(default=False, verbose_name="Confidentiel")
    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.STAFF,
        verbose_name="Visibilité",
        help_text="Qui peut voir et télécharger ce document.",
    )
    allowed_roles = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Rôles autorisés",
        help_text="Liste de rôles (séparés par des virgules) si la visibilité est « Rôles spécifiques ».",
    )
    linked_member = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name="Membre lié",
    )
    linked_app = models.CharField(max_length=50, blank=True, verbose_name="Application liée")
    linked_object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name="ID objet lié")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
        verbose_name="Importé par",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def file_size_display(self):
        size = self.file_size
        if size < 1024:
            return f"{size} o"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} Ko"
        elif size < 1024 * 1024 * 1024:
            return f"{size / (1024 * 1024):.1f} Mo"
        return f"{size / (1024 * 1024 * 1024):.1f} Go"

    @property
    def extension(self):
        if '.' in self.file_name:
            return self.file_name.rsplit('.', 1)[-1].lower()
        return ''

    @property
    def is_pdf(self):
        return self.file_type == 'application/pdf' or self.extension == 'pdf'

    @property
    def is_previewable(self):
        return self.media_type in ('image', 'audio', 'video') or self.is_pdf or self.extension in (
            'txt', 'csv', 'json', 'xml', 'md', 'log', 'yml', 'yaml', 'ini', 'conf', 'html', 'css',
            'docx', 'xlsx', 'pptx',
        )

    @property
    def tags_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []

    @property
    def allowed_roles_list(self):
        if self.allowed_roles:
            return [r.strip() for r in self.allowed_roles.split(',') if r.strip()]
        return []

    def can_be_accessed_by(self, user) -> bool:
        """Vérifie si `user` peut accéder à ce document d'après la visibilité."""
        if not user or not user.is_authenticated:
            return False

        # Super admins / admins : accès total
        if user.is_superuser or getattr(user, 'is_admin', False):
            return True
        if hasattr(user, 'has_any_role') and user.has_any_role('admin', 'secretariat'):
            return True

        # Propriétaire : toujours accès
        if self.uploaded_by_id and self.uploaded_by_id == user.id:
            return True

        # Document confidentiel : réservé aux admins/secrétariat (déjà filtrés plus haut)
        if self.is_confidential:
            return False

        vis = self.visibility or self.Visibility.STAFF
        if vis == self.Visibility.PUBLIC:
            return True
        if vis == self.Visibility.PRIVATE:
            return False  # seul l'uploader + admins, déjà traités
        if vis == self.Visibility.STAFF:
            return hasattr(user, 'has_any_role') and user.has_any_role(*self.STAFF_ROLES)
        if vis == self.Visibility.ROLES:
            roles = self.allowed_roles_list
            if not roles:
                return False
            return hasattr(user, 'has_any_role') and user.has_any_role(*roles)
        return False

    @classmethod
    def accessible_queryset(cls, user):
        """Retourne un queryset filtré selon la visibilité pour `user`."""
        qs = cls.objects.all()
        if not user or not user.is_authenticated:
            return qs.none()

        # Accès total pour admins
        if user.is_superuser or getattr(user, 'is_admin', False):
            return qs
        if hasattr(user, 'has_any_role') and user.has_any_role('admin', 'secretariat'):
            return qs

        # Masquer les confidentiels aux non-admins
        qs = qs.filter(is_confidential=False)

        # Filtrer par visibilité
        conditions = Q(uploaded_by=user) | Q(visibility=cls.Visibility.PUBLIC)

        is_staff_role = hasattr(user, 'has_any_role') and user.has_any_role(*cls.STAFF_ROLES)
        if is_staff_role:
            conditions |= Q(visibility=cls.Visibility.STAFF)

        # Rôles spécifiques : match si un des rôles de l'utilisateur figure dans allowed_roles
        if hasattr(user, 'get_roles_list'):
            user_roles = user.get_roles_list()
            role_q = Q()
            for r in user_roles:
                if r:
                    role_q |= Q(allowed_roles__iregex=r'(^|,)\s*' + r + r'\s*($|,)')
            if role_q:
                conditions |= Q(visibility=cls.Visibility.ROLES) & role_q

        return qs.filter(conditions).distinct()


class GeneratedDocument(models.Model):
    """Document type généré via l'éditeur (compte-rendu, courrier, convocation, etc.)."""

    class Kind(models.TextChoices):
        COMPTE_RENDU = 'compte_rendu', 'Compte-rendu de réunion'
        COURRIER = 'courrier', 'Courrier officiel'
        CONVOCATION = 'convocation', 'Convocation'
        ATTESTATION = 'attestation', 'Attestation'
        NOTE_SERVICE = 'note_service', 'Note de service'
        RAPPORT = 'rapport', 'Rapport'
        AUTRE = 'autre', 'Autre document'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        FINALIZED = 'finalized', 'Finalisé'

    title = models.CharField(max_length=255, verbose_name="Titre")
    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.COURRIER,
        verbose_name="Type de document",
    )
    reference = models.CharField(
        max_length=80, blank=True,
        verbose_name="Référence",
        help_text="Ex. : EEBC/CR/2026/04 (généré automatiquement si vide).",
    )
    document_date = models.DateField(verbose_name="Date du document")
    recipient_name = models.CharField(max_length=200, blank=True, verbose_name="Destinataire")
    recipient_address = models.TextField(blank=True, verbose_name="Adresse du destinataire")
    subject = models.CharField(max_length=255, blank=True, verbose_name="Objet")
    body_html = models.TextField(verbose_name="Contenu", blank=True)
    signature_name = models.CharField(max_length=120, blank=True, verbose_name="Signataire")
    signature_title = models.CharField(max_length=160, blank=True, verbose_name="Fonction du signataire")
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Statut",
    )
    visibility = models.CharField(
        max_length=10,
        choices=Document.Visibility.choices,
        default=Document.Visibility.STAFF,
        verbose_name="Visibilité",
    )
    allowed_roles = models.CharField(max_length=255, blank=True, verbose_name="Rôles autorisés")
    generated_document = models.ForeignKey(
        Document,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='generated_from',
        verbose_name="Document PDF généré",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='generated_documents',
        verbose_name="Créé par",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document généré"
        verbose_name_plural = "Documents générés"
        ordering = ['-updated_at']

    def __str__(self):
        return f"[{self.get_kind_display()}] {self.title}"

    @property
    def allowed_roles_list(self):
        if self.allowed_roles:
            return [r.strip() for r in self.allowed_roles.split(',') if r.strip()]
        return []

    def can_be_accessed_by(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser or getattr(user, 'is_admin', False):
            return True
        if hasattr(user, 'has_any_role') and user.has_any_role('admin', 'secretariat'):
            return True
        if self.created_by_id and self.created_by_id == user.id:
            return True
        vis = self.visibility
        if vis == Document.Visibility.PUBLIC:
            return True
        if vis == Document.Visibility.PRIVATE:
            return False
        if vis == Document.Visibility.STAFF:
            return hasattr(user, 'has_any_role') and user.has_any_role(*Document.STAFF_ROLES)
        if vis == Document.Visibility.ROLES:
            roles = self.allowed_roles_list
            return bool(roles) and hasattr(user, 'has_any_role') and user.has_any_role(*roles)
        return False

    def generate_reference(self):
        if self.reference:
            return self.reference
        prefix_map = {
            self.Kind.COMPTE_RENDU: 'CR',
            self.Kind.COURRIER: 'COU',
            self.Kind.CONVOCATION: 'CONV',
            self.Kind.ATTESTATION: 'ATT',
            self.Kind.NOTE_SERVICE: 'NS',
            self.Kind.RAPPORT: 'RAP',
            self.Kind.AUTRE: 'DOC',
        }
        prefix = prefix_map.get(self.kind, 'DOC')
        year = (self.document_date or self.created_at or models.functions.Now()).year if hasattr(self.document_date or self.created_at, 'year') else 2026
        # Numéro séquentiel : nombre de docs du même type cette année + 1
        from django.utils import timezone
        year = (self.document_date or timezone.now().date()).year
        count = GeneratedDocument.objects.filter(
            kind=self.kind,
            document_date__year=year,
        ).exclude(pk=self.pk).count() + 1
        return f"EEBC/{prefix}/{year}/{count:03d}"


class DocumentShare(models.Model):
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='shares',
        verbose_name="Document",
    )
    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='document_shares',
        verbose_name="Partagé par",
    )
    recipient_email = models.EmailField(verbose_name="Email destinataire")
    recipient_name = models.CharField(max_length=150, blank=True, verbose_name="Nom destinataire")
    message = models.TextField(blank=True, verbose_name="Message")
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField(verbose_name="Expire le")
    accessed_at = models.DateTimeField(null=True, blank=True, verbose_name="Consulté le")
    shared_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Partage de document"
        verbose_name_plural = "Partages de documents"
        ordering = ['-shared_at']

    def __str__(self):
        return f"{self.document.title} → {self.recipient_email}"

    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class DocumentAccess(models.Model):
    class Action(models.TextChoices):
        VIEW = 'view', 'Consultation'
        DOWNLOAD = 'download', 'Téléchargement'
        SHARE = 'share', 'Partage'

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='access_logs',
        verbose_name="Document",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='document_accesses',
        verbose_name="Utilisateur",
    )
    action = models.CharField(max_length=10, choices=Action.choices, verbose_name="Action")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Accès document"
        verbose_name_plural = "Accès documents"
        ordering = ['-accessed_at']

    def __str__(self):
        return f"{self.action} — {self.document.title}"
