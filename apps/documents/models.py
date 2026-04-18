import uuid
from django.conf import settings
from django.db import models
from django.utils.text import slugify


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

    title = models.CharField(max_length=255, verbose_name="Titre")
    description = models.TextField(blank=True, verbose_name="Description")
    file = models.FileField(upload_to='documents/%Y/%m/', verbose_name="Fichier")
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
    def is_previewable(self):
        return self.media_type in ('image', 'audio', 'video') or self.file_type == 'application/pdf' or self.extension in (
            'txt', 'csv', 'json', 'xml', 'md', 'log', 'yml', 'yaml', 'ini', 'conf', 'html', 'css',
            'docx', 'xlsx', 'pptx',
        )

    @property
    def tags_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(',') if t.strip()]
        return []


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
