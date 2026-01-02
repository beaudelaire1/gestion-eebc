"""
Module Public - Modèles pour le site vitrine.

Ce module gère :
- Les pages de contenu (À propos, Contact, etc.)
- Les actualités/annonces publiques
- Les demandes de contact/prière
- Les témoignages
"""

from django.db import models
from django.conf import settings
from django.utils.text import slugify


class Page(models.Model):
    """
    Page de contenu statique pour le site vitrine.
    
    Ex: À propos, Notre histoire, Nos croyances, etc.
    """
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name="URL")
    
    content = models.TextField(verbose_name="Contenu")
    excerpt = models.TextField(blank=True, verbose_name="Résumé", help_text="Court résumé pour les aperçus")
    
    image = models.ImageField(
        upload_to='public/pages/',
        blank=True, null=True,
        verbose_name="Image"
    )
    
    # SEO
    meta_title = models.CharField(max_length=70, blank=True, verbose_name="Titre SEO")
    meta_description = models.CharField(max_length=160, blank=True, verbose_name="Description SEO")
    
    # Affichage
    is_published = models.BooleanField(default=False, verbose_name="Publié")
    show_in_menu = models.BooleanField(default=False, verbose_name="Afficher dans le menu")
    menu_order = models.PositiveIntegerField(default=0, verbose_name="Ordre dans le menu")
    
    # Métadonnées
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Auteur"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Page"
        verbose_name_plural = "Pages"
        ordering = ['menu_order', 'title']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class NewsArticle(models.Model):
    """
    Article d'actualité pour le site vitrine.
    """
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(max_length=200, unique=True, blank=True, verbose_name="URL")
    
    content = models.TextField(verbose_name="Contenu")
    excerpt = models.TextField(blank=True, verbose_name="Résumé")
    
    image = models.ImageField(
        upload_to='public/news/',
        blank=True, null=True,
        verbose_name="Image"
    )
    
    # Catégorie
    category = models.ForeignKey(
        'NewsCategory',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='articles',
        verbose_name="Catégorie"
    )
    
    # Site concerné (optionnel)
    site = models.ForeignKey(
        'core.Site',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='news_articles',
        verbose_name="Site",
        help_text="Laisser vide pour une actualité globale"
    )
    
    # Publication
    is_published = models.BooleanField(default=False, verbose_name="Publié")
    is_featured = models.BooleanField(default=False, verbose_name="À la une")
    publish_date = models.DateTimeField(verbose_name="Date de publication")
    
    # Métadonnées
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Auteur"
    )
    views_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de vues")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Actualité"
        verbose_name_plural = "Actualités"
        ordering = ['-publish_date']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class NewsCategory(models.Model):
    """Catégorie d'actualités."""
    name = models.CharField(max_length=100, verbose_name="Nom")
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    color = models.CharField(max_length=7, default="#0d6efd", verbose_name="Couleur")
    
    class Meta:
        verbose_name = "Catégorie d'actualité"
        verbose_name_plural = "Catégories d'actualités"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ContactRequest(models.Model):
    """
    Demande de contact depuis le site vitrine.
    """
    class RequestType(models.TextChoices):
        GENERAL = 'general', 'Question générale'
        PRAYER = 'prayer', 'Demande de prière'
        VISIT = 'visit', 'Demande de visite'
        INFO = 'info', 'Demande d\'information'
        TESTIMONY = 'testimony', 'Témoignage'
        OTHER = 'other', 'Autre'
    
    class Status(models.TextChoices):
        NEW = 'new', 'Nouveau'
        IN_PROGRESS = 'in_progress', 'En cours'
        COMPLETED = 'completed', 'Traité'
        ARCHIVED = 'archived', 'Archivé'
    
    # Informations du demandeur
    name = models.CharField(max_length=200, verbose_name="Nom")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    
    # Demande
    request_type = models.CharField(
        max_length=15,
        choices=RequestType.choices,
        default=RequestType.GENERAL,
        verbose_name="Type de demande"
    )
    subject = models.CharField(max_length=200, verbose_name="Sujet")
    message = models.TextField(verbose_name="Message")
    
    # Site préféré
    preferred_site = models.ForeignKey(
        'core.Site',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contact_requests',
        verbose_name="Site préféré"
    )
    
    # Traitement
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name="Statut"
    )
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_contact_requests',
        verbose_name="Assigné à"
    )
    
    internal_notes = models.TextField(blank=True, verbose_name="Notes internes")
    
    # Consentement RGPD
    consent_given = models.BooleanField(default=False, verbose_name="Consentement RGPD")
    
    # Métadonnées
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Demande de contact"
        verbose_name_plural = "Demandes de contact"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"


class Testimony(models.Model):
    """
    Témoignage publié sur le site vitrine.
    """
    author_name = models.CharField(max_length=200, verbose_name="Nom de l'auteur")
    author_photo = models.ImageField(
        upload_to='public/testimonies/',
        blank=True, null=True,
        verbose_name="Photo"
    )
    
    title = models.CharField(max_length=200, blank=True, verbose_name="Titre")
    content = models.TextField(verbose_name="Témoignage")
    
    # Lien avec un membre (optionnel)
    member = models.ForeignKey(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='testimonies',
        verbose_name="Membre"
    )
    
    # Publication
    is_published = models.BooleanField(default=False, verbose_name="Publié")
    is_featured = models.BooleanField(default=False, verbose_name="À la une")
    publish_date = models.DateField(null=True, blank=True, verbose_name="Date de publication")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Témoignage"
        verbose_name_plural = "Témoignages"
        ordering = ['-publish_date', '-created_at']
    
    def __str__(self):
        return f"Témoignage de {self.author_name}"


class WorshipSchedule(models.Model):
    """
    Horaire de culte affiché sur le site vitrine.
    """
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 1, 'Lundi'
        TUESDAY = 2, 'Mardi'
        WEDNESDAY = 3, 'Mercredi'
        THURSDAY = 4, 'Jeudi'
        FRIDAY = 5, 'Vendredi'
        SATURDAY = 6, 'Samedi'
        SUNDAY = 7, 'Dimanche'
    
    site = models.ForeignKey(
        'core.Site',
        on_delete=models.CASCADE,
        related_name='worship_schedules',
        verbose_name="Site"
    )
    
    name = models.CharField(max_length=100, verbose_name="Nom du service")
    day_of_week = models.IntegerField(choices=DayOfWeek.choices, verbose_name="Jour")
    start_time = models.TimeField(verbose_name="Heure de début")
    end_time = models.TimeField(blank=True, null=True, verbose_name="Heure de fin")
    
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    class Meta:
        verbose_name = "Horaire de culte"
        verbose_name_plural = "Horaires de culte"
        ordering = ['site', 'day_of_week', 'start_time']
    
    def __str__(self):
        return f"{self.site.name} - {self.get_day_of_week_display()} {self.start_time}"
