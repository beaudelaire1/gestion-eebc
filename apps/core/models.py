"""
Module Core - Modèles fondamentaux pour la gestion multi-sites.

Ce module gère :
- Les sites paroissiaux (Cabassou, Macouria)
- Les villes et quartiers
- Les familles et liens de parenté
"""

from django.db import models
from django.conf import settings


class Site(models.Model):
    """
    Site paroissial (Cabassou, Macouria, ou autre).
    
    Chaque site a ses propres paramètres, responsables et données.
    Permet une gestion séparée tout en offrant une vue consolidée.
    """
    
    code = models.CharField(
        max_length=5,
        unique=True,
        verbose_name="Code",
        help_text="Code court unique (ex: CAB, MAC). Utilisé pour générer les IDs membres."
    )
    
    name = models.CharField(max_length=100, verbose_name="Nom")
    
    address = models.TextField(blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Code postal")
    
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")
    
    # Coordonnées GPS pour la carte
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        verbose_name="Latitude"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        verbose_name="Longitude"
    )
    
    # Horaires des cultes
    worship_schedule = models.TextField(
        blank=True,
        verbose_name="Horaires des cultes",
        help_text="Ex: Dimanche 9h et 11h"
    )
    
    # Responsables
    pastor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='pastored_sites',
        verbose_name="Pasteur"
    )
    
    administrators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='administered_sites',
        verbose_name="Administrateurs"
    )
    
    # Paramètres
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    is_main_site = models.BooleanField(
        default=False,
        verbose_name="Site principal",
        help_text="Le site principal pour les vues consolidées"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Site"
        verbose_name_plural = "Sites"
        ordering = ['-is_main_site', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def save(self, *args, **kwargs):
        # Un seul site principal
        if self.is_main_site:
            Site.objects.filter(is_main_site=True).exclude(pk=self.pk).update(is_main_site=False)
        super().save(*args, **kwargs)


class City(models.Model):
    """
    Ville/Commune de Guyane.
    
    Ex: Cayenne, Matoury, Rémire-Montjoly, Macouria
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="Nom")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Code postal")
    
    # Coordonnées GPS du centre-ville
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        verbose_name="Latitude"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        verbose_name="Longitude"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    class Meta:
        verbose_name = "Ville"
        verbose_name_plural = "Villes"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def neighborhood_count(self):
        return self.neighborhoods.count()
    
    @property
    def family_count(self):
        return Family.objects.filter(neighborhood__city=self).count()


class Neighborhood(models.Model):
    """
    Quartier d'une ville.
    
    Ex: Balata, Cogneau, Tonate, Soula
    Utilisé pour le recensement et les missions d'évangélisation.
    """
    name = models.CharField(max_length=100, verbose_name="Nom")
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='neighborhoods',
        verbose_name="Ville"
    )
    
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Coordonnées GPS du centre du quartier
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        verbose_name="Latitude"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        verbose_name="Longitude"
    )
    
    # Statistiques de recensement
    estimated_population = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name="Population estimée"
    )
    
    last_census_date = models.DateField(
        null=True, blank=True,
        verbose_name="Dernier recensement"
    )
    
    # Responsable de zone
    zone_leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='led_neighborhoods',
        verbose_name="Responsable de zone"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    class Meta:
        verbose_name = "Quartier"
        verbose_name_plural = "Quartiers"
        ordering = ['city__name', 'name']
        unique_together = ['name', 'city']
    
    def __str__(self):
        return f"{self.name} ({self.city.name})"
    
    @property
    def family_count(self):
        return self.families.count()


class Family(models.Model):
    """
    Famille/Foyer regroupant plusieurs membres.
    
    Permet de gérer les liens familiaux et d'avoir une vue
    par foyer pour les statistiques et la communication.
    """
    name = models.CharField(
        max_length=100,
        verbose_name="Nom de famille",
        help_text="Ex: Famille DUPONT"
    )
    
    # Localisation
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='families',
        verbose_name="Site"
    )
    
    neighborhood = models.ForeignKey(
        Neighborhood,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='families',
        verbose_name="Quartier"
    )
    
    # Adresse
    address = models.TextField(blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Code postal")
    
    # Coordonnées GPS pour la carte
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        verbose_name="Latitude"
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True,
        verbose_name="Longitude"
    )
    
    # Contact principal
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email")
    
    # Chef de famille (référence vers Member, ajouté après)
    # head_of_family sera ajouté via ForeignKey dans Member
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    is_active = models.BooleanField(default=True, verbose_name="Active")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Famille"
        verbose_name_plural = "Familles"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def member_count(self):
        return self.members.count()
    
    @property
    def head(self):
        """Retourne le chef de famille."""
        return self.members.filter(family_role='HEAD').first()


class FamilyRelationship(models.Model):
    """
    Relation entre deux membres d'une famille.
    
    Permet de définir les liens de parenté précis :
    père/mère, fils/fille, conjoint, frère/sœur, etc.
    """
    
    class RelationType(models.TextChoices):
        SPOUSE = 'spouse', 'Conjoint(e)'
        PARENT = 'parent', 'Parent'
        CHILD = 'child', 'Enfant'
        SIBLING = 'sibling', 'Frère/Sœur'
        GRANDPARENT = 'grandparent', 'Grand-parent'
        GRANDCHILD = 'grandchild', 'Petit-enfant'
        UNCLE_AUNT = 'uncle_aunt', 'Oncle/Tante'
        NEPHEW_NIECE = 'nephew_niece', 'Neveu/Nièce'
        COUSIN = 'cousin', 'Cousin(e)'
        IN_LAW = 'in_law', 'Beau-parent/Belle-famille'
        OTHER = 'other', 'Autre'
    
    from_member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='relationships_from',
        verbose_name="Membre"
    )
    
    to_member = models.ForeignKey(
        'members.Member',
        on_delete=models.CASCADE,
        related_name='relationships_to',
        verbose_name="Lié à"
    )
    
    relationship_type = models.CharField(
        max_length=15,
        choices=RelationType.choices,
        verbose_name="Type de relation"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Relation familiale"
        verbose_name_plural = "Relations familiales"
        unique_together = ['from_member', 'to_member']
    
    def __str__(self):
        return f"{self.from_member} → {self.get_relationship_type_display()} → {self.to_member}"


# =============================================================================
# MISSIONS ET ÉVANGÉLISATION
# =============================================================================

class MissionCampaign(models.Model):
    """
    Campagne de mission/évangélisation dans un quartier.
    
    Permet de planifier et suivre les missions de visite
    et d'évangélisation par quartier.
    """
    
    class Status(models.TextChoices):
        PLANNED = 'planned', 'Planifiée'
        IN_PROGRESS = 'in_progress', 'En cours'
        COMPLETED = 'completed', 'Terminée'
        CANCELLED = 'cancelled', 'Annulée'
    
    name = models.CharField(max_length=200, verbose_name="Nom")
    description = models.TextField(blank=True, verbose_name="Description")
    
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='mission_campaigns',
        verbose_name="Site"
    )
    
    neighborhoods = models.ManyToManyField(
        Neighborhood,
        related_name='mission_campaigns',
        verbose_name="Quartiers ciblés"
    )
    
    start_date = models.DateField(verbose_name="Date de début")
    end_date = models.DateField(verbose_name="Date de fin")
    
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PLANNED,
        verbose_name="Statut"
    )
    
    # Équipe
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='led_missions',
        verbose_name="Responsable"
    )
    
    team_members = models.ManyToManyField(
        'members.Member',
        blank=True,
        related_name='mission_participations',
        verbose_name="Équipe"
    )
    
    # Résultats
    homes_visited = models.PositiveIntegerField(default=0, verbose_name="Foyers visités")
    contacts_made = models.PositiveIntegerField(default=0, verbose_name="Contacts établis")
    decisions_made = models.PositiveIntegerField(default=0, verbose_name="Décisions")
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Campagne de mission"
        verbose_name_plural = "Campagnes de mission"
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.name} ({self.start_date})"


# =============================================================================
# SITE VITRINE PUBLIC
# =============================================================================

class PageContent(models.Model):
    """
    Contenu des pages du site vitrine.
    
    Permet de gérer le contenu statique des pages :
    Accueil, À propos, Contact, etc.
    """
    
    class PageType(models.TextChoices):
        HOME = 'home', 'Page d\'accueil'
        ABOUT = 'about', 'À propos'
        BELIEFS = 'beliefs', 'Nos croyances'
        CONTACT = 'contact', 'Contact'
        HISTORY = 'history', 'Notre histoire'
        MINISTRIES = 'ministries', 'Ministères'
        CUSTOM = 'custom', 'Page personnalisée'
    
    page_type = models.CharField(
        max_length=20,
        choices=PageType.choices,
        verbose_name="Type de page"
    )
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="URL",
        help_text="Identifiant unique pour l'URL (ex: a-propos)"
    )
    
    # Contenu
    subtitle = models.CharField(max_length=300, blank=True, verbose_name="Sous-titre")
    content = models.TextField(verbose_name="Contenu", help_text="Supporte le format HTML")
    
    # Image d'en-tête
    header_image = models.ImageField(
        upload_to='public/pages/',
        blank=True, null=True,
        verbose_name="Image d'en-tête"
    )
    
    # SEO
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        verbose_name="Description SEO",
        help_text="Description pour les moteurs de recherche (max 160 caractères)"
    )
    
    # Paramètres
    is_published = models.BooleanField(default=False, verbose_name="Publié")
    show_in_menu = models.BooleanField(default=True, verbose_name="Afficher dans le menu")
    menu_order = models.PositiveIntegerField(default=0, verbose_name="Ordre dans le menu")
    
    # Métadonnées
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='authored_pages',
        verbose_name="Auteur"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Page du site"
        verbose_name_plural = "Pages du site"
        ordering = ['menu_order', 'title']
    
    def __str__(self):
        status = "✓" if self.is_published else "○"
        return f"{status} {self.title}"


class NewsArticle(models.Model):
    """
    Article d'actualité pour le site vitrine.
    
    Permet de publier des nouvelles, annonces et témoignages
    visibles par le grand public.
    """
    
    class Category(models.TextChoices):
        NEWS = 'news', 'Actualité'
        ANNOUNCEMENT = 'announcement', 'Annonce'
        TESTIMONY = 'testimony', 'Témoignage'
        DEVOTIONAL = 'devotional', 'Méditation'
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="URL"
    )
    
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.NEWS,
        verbose_name="Catégorie"
    )
    
    # Contenu
    excerpt = models.TextField(
        max_length=500,
        verbose_name="Résumé",
        help_text="Court résumé affiché dans la liste des articles"
    )
    content = models.TextField(verbose_name="Contenu", help_text="Supporte le format HTML")
    
    # Image
    featured_image = models.ImageField(
        upload_to='public/news/',
        blank=True, null=True,
        verbose_name="Image à la une"
    )
    
    # Site concerné (optionnel)
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='news_articles',
        verbose_name="Site",
        help_text="Laisser vide pour un article global"
    )
    
    # Auteur (requis pour les méditations, optionnel pour les actus)
    author_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom de l'auteur",
        help_text="Requis pour les méditations"
    )
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='news_articles',
        verbose_name="Auteur (utilisateur)",
        help_text="Utilisateur interne qui a créé l'article"
    )
    
    # Paramètres de publication
    is_published = models.BooleanField(default=False, verbose_name="Publié")
    is_featured = models.BooleanField(
        default=False,
        verbose_name="À la une",
        help_text="Afficher en priorité sur la page d'accueil"
    )
    
    # Dates de publication
    publish_date = models.DateTimeField(
        verbose_name="Date de publication",
        help_text="L'article sera visible à partir de cette date"
    )
    
    # Dates d'affichage (pour gestion interne)
    display_start_date = models.DateField(
        null=True, blank=True,
        verbose_name="Début d'affichage",
        help_text="Date à partir de laquelle l'article est affiché (optionnel)"
    )
    
    display_end_date = models.DateField(
        null=True, blank=True,
        verbose_name="Fin d'affichage",
        help_text="Date jusqu'à laquelle l'article est affiché (optionnel)"
    )
    
    # Métadonnées
    views_count = models.PositiveIntegerField(default=0, verbose_name="Nombre de vues")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ['-publish_date']
    
    def __str__(self):
        status = "✓" if self.is_published else "○"
        return f"{status} {self.title}"
    
    @property
    def is_visible(self):
        """Vérifie si l'article est visible publiquement."""
        from django.utils import timezone
        from datetime import date
        
        if not self.is_published:
            return False
        
        if self.publish_date > timezone.now():
            return False
        
        today = date.today()
        
        if self.display_start_date and self.display_start_date > today:
            return False
        
        if self.display_end_date and self.display_end_date < today:
            return False
        
        return True
    
    @property
    def display_author(self):
        """Retourne le nom de l'auteur à afficher."""
        if self.author_name:
            return self.author_name
        if self.author:
            return self.author.get_full_name() or self.author.username
        return None
    
    @property
    def requires_author(self):
        """Les méditations nécessitent un auteur."""
        return self.category == self.Category.DEVOTIONAL


class ContactMessage(models.Model):
    """
    Message de contact envoyé via le formulaire public.
    
    Permet aux visiteurs de contacter l'église.
    """
    
    class Status(models.TextChoices):
        NEW = 'new', 'Nouveau'
        READ = 'read', 'Lu'
        REPLIED = 'replied', 'Répondu'
        ARCHIVED = 'archived', 'Archivé'
    
    class Subject(models.TextChoices):
        GENERAL = 'general', 'Question générale'
        VISIT = 'visit', 'Je souhaite visiter'
        PRAYER = 'prayer', 'Demande de prière'
        INFO = 'info', 'Demande d\'information'
        TESTIMONY = 'testimony', 'Partager un témoignage'
        OTHER = 'other', 'Autre'
    
    # Informations du visiteur
    name = models.CharField(max_length=100, verbose_name="Nom")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    
    # Message
    subject = models.CharField(
        max_length=20,
        choices=Subject.choices,
        default=Subject.GENERAL,
        verbose_name="Sujet"
    )
    message = models.TextField(verbose_name="Message")
    
    # Site concerné
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contact_messages',
        verbose_name="Site"
    )
    
    # Suivi
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name="Statut"
    )
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_messages',
        verbose_name="Assigné à"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes internes")
    
    # Métadonnées
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Reçu le")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="Lu le")
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name="Répondu le")
    
    class Meta:
        verbose_name = "Message de contact"
        verbose_name_plural = "Messages de contact"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.get_subject_display()}"
    
    def mark_as_read(self):
        if self.status == self.Status.NEW:
            from django.utils import timezone
            self.status = self.Status.READ
            self.read_at = timezone.now()
            self.save(update_fields=['status', 'read_at'])


class VisitorRegistration(models.Model):
    """
    Inscription d'un visiteur via le site public.
    
    Permet aux personnes intéressées de s'inscrire pour :
    - Recevoir des informations
    - Être contacté
    - Participer à un événement
    """
    
    class Interest(models.TextChoices):
        VISIT = 'visit', 'Visiter l\'église'
        INFO = 'info', 'Recevoir des informations'
        BIBLE_STUDY = 'bible_study', 'Étude biblique'
        YOUTH = 'youth', 'Groupe de jeunes'
        CHILDREN = 'children', 'Club biblique enfants'
        VOLUNTEER = 'volunteer', 'Devenir bénévole'
        OTHER = 'other', 'Autre'
    
    # Informations personnelles
    first_name = models.CharField(max_length=100, verbose_name="Prénom")
    last_name = models.CharField(max_length=100, verbose_name="Nom")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    
    # Adresse (optionnel)
    address = models.TextField(blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=100, blank=True, verbose_name="Ville")
    neighborhood = models.ForeignKey(
        Neighborhood,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='visitor_registrations',
        verbose_name="Quartier"
    )
    
    # Intérêt
    interest = models.CharField(
        max_length=20,
        choices=Interest.choices,
        default=Interest.VISIT,
        verbose_name="Intérêt"
    )
    
    message = models.TextField(blank=True, verbose_name="Message")
    
    # Site préféré
    preferred_site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='visitor_registrations',
        verbose_name="Site préféré"
    )
    
    # Suivi
    is_contacted = models.BooleanField(default=False, verbose_name="Contacté")
    contacted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='contacted_visitors',
        verbose_name="Contacté par"
    )
    contacted_at = models.DateTimeField(null=True, blank=True, verbose_name="Contacté le")
    
    # Conversion en membre
    converted_to_member = models.OneToOneField(
        'members.Member',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='visitor_registration',
        verbose_name="Converti en membre"
    )
    
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Inscrit le")
    
    class Meta:
        verbose_name = "Inscription visiteur"
        verbose_name_plural = "Inscriptions visiteurs"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_interest_display()}"


class PublicEvent(models.Model):
    """
    Événement public visible sur le site vitrine.
    
    Lié à un Event interne mais avec des informations
    supplémentaires pour l'affichage public.
    """
    
    # Lien avec l'événement interne (optionnel)
    internal_event = models.OneToOneField(
        'events.Event',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='public_event',
        verbose_name="Événement interne"
    )
    
    # Informations publiques
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL")
    
    description = models.TextField(verbose_name="Description")
    
    # Date et lieu
    start_date = models.DateField(verbose_name="Date de début")
    start_time = models.TimeField(null=True, blank=True, verbose_name="Heure de début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date de fin")
    end_time = models.TimeField(null=True, blank=True, verbose_name="Heure de fin")
    
    location = models.CharField(max_length=200, blank=True, verbose_name="Lieu")
    address = models.TextField(blank=True, verbose_name="Adresse")
    
    # Site
    site = models.ForeignKey(
        Site,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='public_events',
        verbose_name="Site"
    )
    
    # Image
    image = models.ImageField(
        upload_to='public/events/',
        blank=True, null=True,
        verbose_name="Image"
    )
    
    # Paramètres
    is_published = models.BooleanField(default=False, verbose_name="Publié")
    is_featured = models.BooleanField(default=False, verbose_name="À la une")
    allow_registration = models.BooleanField(
        default=False,
        verbose_name="Inscription en ligne",
        help_text="Permettre aux visiteurs de s'inscrire"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Événement public"
        verbose_name_plural = "Événements publics"
        ordering = ['start_date', 'start_time']
    
    def __str__(self):
        return f"{self.title} - {self.start_date}"
    
    @property
    def is_upcoming(self):
        from datetime import date
        return self.start_date >= date.today()


class Slider(models.Model):
    """
    Slide pour le carrousel de la page d'accueil.
    """
    title = models.CharField(max_length=200, verbose_name="Titre")
    subtitle = models.CharField(max_length=300, blank=True, verbose_name="Sous-titre")
    
    image = models.ImageField(
        upload_to='public/slider/',
        verbose_name="Image"
    )
    
    # Bouton d'action
    button_text = models.CharField(max_length=50, blank=True, verbose_name="Texte du bouton")
    button_url = models.CharField(max_length=200, blank=True, verbose_name="Lien du bouton")
    
    # Paramètres
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    order = models.PositiveIntegerField(default=0, verbose_name="Ordre")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Slide"
        verbose_name_plural = "Slides"
        ordering = ['order']
    
    def __str__(self):
        return self.title


class SiteSettings(models.Model):
    """
    Paramètres globaux du site vitrine.
    
    Singleton - une seule instance.
    """
    # Informations générales
    site_name = models.CharField(
        max_length=100,
        default="EEBC",
        verbose_name="Nom du site"
    )
    tagline = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Slogan"
    )
    
    # Logo
    logo = models.ImageField(
        upload_to='public/settings/',
        blank=True, null=True,
        verbose_name="Logo"
    )
    favicon = models.ImageField(
        upload_to='public/settings/',
        blank=True, null=True,
        verbose_name="Favicon"
    )
    
    # Contact principal
    email = models.EmailField(blank=True, verbose_name="Email de contact")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    
    # Réseaux sociaux
    facebook_url = models.URLField(blank=True, verbose_name="Facebook")
    youtube_url = models.URLField(blank=True, verbose_name="YouTube")
    instagram_url = models.URLField(blank=True, verbose_name="Instagram")
    
    # SEO
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        verbose_name="Description SEO par défaut"
    )
    
    # Footer
    footer_text = models.TextField(blank=True, verbose_name="Texte du pied de page")
    
    # Maintenance
    maintenance_mode = models.BooleanField(
        default=False,
        verbose_name="Mode maintenance"
    )
    maintenance_message = models.TextField(
        blank=True,
        verbose_name="Message de maintenance"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Paramètres du site"
        verbose_name_plural = "Paramètres du site"
    
    def __str__(self):
        return "Paramètres du site vitrine"
    
    def save(self, *args, **kwargs):
        # Singleton : une seule instance
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Retourne l'instance unique des paramètres."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


# =============================================================================
# AUDIT LOGGING
# =============================================================================

class AuditLog(models.Model):
    """
    Journal d'audit des actions utilisateurs.
    
    Ce modèle trace toutes les actions sensibles effectuées dans l'application:
    - Connexions/déconnexions
    - Modifications de données sensibles (membres, finances)
    - Exports de données
    - Tentatives d'accès refusées
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    
    class Action(models.TextChoices):
        LOGIN = 'login', 'Connexion'
        LOGOUT = 'logout', 'Déconnexion'
        LOGIN_FAILED = 'login_failed', 'Échec connexion'
        CREATE = 'create', 'Création'
        UPDATE = 'update', 'Modification'
        DELETE = 'delete', 'Suppression'
        EXPORT = 'export', 'Export'
        ACCESS_DENIED = 'access_denied', 'Accès refusé'
        VIEW = 'view', 'Consultation'
        SERVER_ERROR = 'server_error', 'Erreur serveur'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name="Utilisateur"
    )
    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name="Action"
    )
    model_name = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Modèle",
        help_text="Nom du modèle concerné (ex: Member, FinancialTransaction)"
    )
    object_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="ID Objet",
        help_text="Identifiant de l'objet concerné"
    )
    object_repr = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Représentation",
        help_text="Représentation textuelle de l'objet"
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Changements",
        help_text="Détails des modifications (ancien/nouveau)"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Adresse IP"
    )
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="User Agent"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date/Heure"
    )
    
    # Champs additionnels pour plus de contexte
    path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Chemin URL",
        help_text="URL de la requête"
    )
    extra_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Données supplémentaires",
        help_text="Informations additionnelles contextuelles"
    )
    
    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journaux d'audit"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['model_name', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonyme'
        return f"{user_str} - {self.get_action_display()} - {self.timestamp.strftime('%d/%m/%Y %H:%M')}"
    
    @classmethod
    def log(cls, action, user=None, model_name='', object_id='', object_repr='',
            changes=None, ip_address=None, user_agent='', path='', extra_data=None):
        """
        Méthode utilitaire pour créer une entrée d'audit.
        
        Args:
            action: Type d'action (utiliser AuditLog.Action)
            user: Utilisateur effectuant l'action
            model_name: Nom du modèle concerné
            object_id: ID de l'objet concerné
            object_repr: Représentation textuelle de l'objet
            changes: Dict des changements {field: {'old': x, 'new': y}}
            ip_address: Adresse IP du client
            user_agent: User-Agent du navigateur
            path: Chemin URL de la requête
            extra_data: Données supplémentaires
        
        Returns:
            AuditLog: L'entrée d'audit créée
        """
        return cls.objects.create(
            action=action,
            user=user,
            model_name=model_name,
            object_id=str(object_id) if object_id else '',
            object_repr=str(object_repr)[:200] if object_repr else '',
            changes=changes or {},
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else '',
            path=path[:500] if path else '',
            extra_data=extra_data or {}
        )
    
    @classmethod
    def log_from_request(cls, request, action, model_name='', object_id='',
                         object_repr='', changes=None, extra_data=None):
        """
        Crée une entrée d'audit à partir d'une requête HTTP.
        
        Args:
            request: Objet HttpRequest Django
            action: Type d'action
            model_name: Nom du modèle concerné
            object_id: ID de l'objet concerné
            object_repr: Représentation textuelle de l'objet
            changes: Dict des changements
            extra_data: Données supplémentaires
        
        Returns:
            AuditLog: L'entrée d'audit créée
        """
        # Extraire l'IP (gérer les proxies)
        ip_address = cls.get_client_ip(request)
        
        # Extraire le User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Utilisateur (peut être anonyme)
        user = request.user if request.user.is_authenticated else None
        
        return cls.log(
            action=action,
            user=user,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            path=request.path,
            extra_data=extra_data
        )
    
    @staticmethod
    def get_client_ip(request):
        """
        Extrait l'adresse IP du client depuis la requête.
        Gère les cas avec proxy (X-Forwarded-For).
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# =============================================================================
# BACKUP MANAGEMENT
# =============================================================================

class DatabaseBackup(models.Model):
    """
    Modèle pour tracer les sauvegardes de base de données.
    
    Permet de:
    - Lister les sauvegardes disponibles
    - Télécharger les sauvegardes depuis l'admin
    - Suivre le statut des sauvegardes
    
    Requirements: 18.3
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'En cours'
        SUCCESS = 'success', 'Réussie'
        FAILED = 'failed', 'Échouée'
    
    filename = models.CharField(
        max_length=255,
        verbose_name="Nom du fichier",
        help_text="Nom du fichier de sauvegarde"
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name="Chemin du fichier",
        help_text="Chemin complet vers le fichier de sauvegarde"
    )
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name="Taille du fichier (bytes)"
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Statut"
    )
    database_engine = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Moteur de base de données",
        help_text="Type de base de données (SQLite, PostgreSQL, MySQL)"
    )
    
    # Métadonnées de la sauvegarde
    backup_type = models.CharField(
        max_length=20,
        choices=[
            ('automatic', 'Automatique'),
            ('manual', 'Manuelle'),
        ],
        default='automatic',
        verbose_name="Type de sauvegarde"
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_backups',
        verbose_name="Créé par",
        help_text="Utilisateur ayant déclenché la sauvegarde (pour les sauvegardes manuelles)"
    )
    
    # Informations sur l'exécution
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="ID de tâche Celery",
        help_text="Identifiant de la tâche Celery ayant créé cette sauvegarde"
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name="Message d'erreur",
        help_text="Détails de l'erreur en cas d'échec"
    )
    
    # Dates
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Créé le"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Terminé le"
    )
    
    class Meta:
        verbose_name = "Sauvegarde de base de données"
        verbose_name_plural = "Sauvegardes de base de données"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.filename} - {self.get_status_display()}"
    
    @property
    def file_size_mb(self):
        """Retourne la taille du fichier en MB."""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None
    
    @property
    def file_exists(self):
        """Vérifie si le fichier de sauvegarde existe sur le disque."""
        from pathlib import Path
        return Path(self.file_path).exists() if self.file_path else False
    
    def mark_as_success(self, file_size=None):
        """Marque la sauvegarde comme réussie."""
        from django.utils import timezone
        self.status = self.Status.SUCCESS
        self.completed_at = timezone.now()
        if file_size:
            self.file_size = file_size
        self.save(update_fields=['status', 'completed_at', 'file_size'])
    
    def mark_as_failed(self, error_message=''):
        """Marque la sauvegarde comme échouée."""
        from django.utils import timezone
        self.status = self.Status.FAILED
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(update_fields=['status', 'completed_at', 'error_message'])
    
    @classmethod
    def create_backup_record(cls, filename, file_path, backup_type='automatic', 
                           created_by=None, celery_task_id='', database_engine=''):
        """
        Crée un enregistrement de sauvegarde.
        
        Args:
            filename: Nom du fichier de sauvegarde
            file_path: Chemin complet vers le fichier
            backup_type: Type de sauvegarde ('automatic' ou 'manual')
            created_by: Utilisateur ayant déclenché la sauvegarde
            celery_task_id: ID de la tâche Celery
            database_engine: Type de base de données
        
        Returns:
            DatabaseBackup: L'enregistrement créé
        """
        return cls.objects.create(
            filename=filename,
            file_path=file_path,
            backup_type=backup_type,
            created_by=created_by,
            celery_task_id=celery_task_id,
            database_engine=database_engine
        )
    
    @classmethod
    def cleanup_old_records(cls, keep_count=30):
        """
        Supprime les anciens enregistrements de sauvegarde.
        
        Args:
            keep_count: Nombre d'enregistrements à conserver
        """
        if cls.objects.count() > keep_count:
            old_records = cls.objects.all()[keep_count:]
            for record in old_records:
                # Supprimer le fichier physique s'il existe
                if record.file_exists:
                    try:
                        from pathlib import Path
                        Path(record.file_path).unlink()
                    except Exception:
                        pass  # Ignorer les erreurs de suppression de fichier
                
                # Supprimer l'enregistrement
                record.delete()
