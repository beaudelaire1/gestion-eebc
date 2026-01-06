"""
Configuration centralisée de tous les exports du projet.
"""
from django.urls import reverse
from django.contrib.auth.models import Permission


class ExportConfig:
    """Configuration d'un export."""
    
    def __init__(self, name, description, icon, url_name=None, url_kwargs=None, 
                 permissions=None, category=None, format_type='excel', 
                 sensitive=False, filters=None):
        self.name = name
        self.description = description
        self.icon = icon
        self.url_name = url_name
        self.url_kwargs = url_kwargs or {}
        self.permissions = permissions or []
        self.category = category
        self.format_type = format_type  # 'excel', 'pdf', 'csv'
        self.sensitive = sensitive
        self.filters = filters or []
    
    def get_url(self):
        """Retourne l'URL de l'export."""
        if self.url_name:
            return reverse(self.url_name, kwargs=self.url_kwargs)
        return '#'
    
    def has_permission(self, user):
        """Vérifie si l'utilisateur a les permissions nécessaires."""
        if not self.permissions:
            return True
        
        for perm in self.permissions:
            if not user.has_perm(perm):
                return False
        return True


# Configuration de tous les exports disponibles
EXPORT_REGISTRY = {
    # ========================================
    # MEMBRES & ENFANTS
    # ========================================
    'members': ExportConfig(
        name='Membres',
        description='Exporter tous les membres actifs de l\'église',
        icon='bi-people-fill',
        url_name='imports:export_members',
        permissions=['members.view_member'],
        category='Personnes',
        format_type='excel'
    ),
    
    'children': ExportConfig(
        name='Enfants',
        description='Exporter tous les enfants du club biblique',
        icon='bi-person-hearts',
        url_name='imports:export_children',
        permissions=['bibleclub.view_child'],
        category='Personnes',
        format_type='excel'
    ),
    
    # ========================================
    # NOUVEAUX EXPORTS
    # ========================================
    'groups': ExportConfig(
        name='Groupes',
        description='Exporter tous les groupes et ministères de l\'église',
        icon='bi-people',
        url_name='imports:export_groups',
        permissions=['groups.view_group'],
        category='Personnes',
        format_type='excel'
    ),
    
    'inventory': ExportConfig(
        name='Inventaire',
        description='Exporter la liste complète des équipements',
        icon='bi-box-seam',
        url_name='imports:export_inventory',
        permissions=['inventory.view_equipment'],
        category='Gestion',
        format_type='excel'
    ),
    
    'transport': ExportConfig(
        name='Transport',
        description='Exporter les chauffeurs et véhicules disponibles',
        icon='bi-truck',
        url_name='imports:export_transport',
        permissions=['transport.view_driverprofile'],
        category='Gestion',
        format_type='excel'
    ),
    
    'communication': ExportConfig(
        name='Logs Communication',
        description='Exporter l\'historique des emails et SMS (3 mois)',
        icon='bi-envelope-check',
        url_name='imports:export_communication',
        permissions=['communication.view_emaillog'],
        category='Administration',
        format_type='excel',
        sensitive=True
    ),
    
    # ========================================
    # FINANCES (LIENS VERS EXPORTS EXISTANTS)
    # ========================================
    'transactions': ExportConfig(
        name='Transactions',
        description='Exporter les transactions financières avec filtres',
        icon='bi-cash-stack',
        url_name='finance:transactions_export_excel',
        permissions=['finance.view_financialtransaction'],
        category='Finances',
        format_type='excel',
        sensitive=True,
        filters=['date_debut', 'date_fin', 'type', 'categorie']
    ),
    
    'budgets_list': ExportConfig(
        name='Liste des Budgets',
        description='Exporter la liste de tous les budgets par année',
        icon='bi-pie-chart-fill',
        url_name='finance:budget_list_export_excel',
        permissions=['finance.view_budget'],
        category='Finances',
        format_type='excel',
        sensitive=True,
        filters=['annee', 'statut']
    ),
    
    # ========================================
    # ÉVÉNEMENTS (LIENS VERS EXPORTS EXISTANTS)
    # ========================================
    'calendar_pdf': ExportConfig(
        name='Calendrier',
        description='Télécharger le calendrier des événements en PDF',
        icon='bi-calendar-event',
        url_name='events:calendar_pdf',
        permissions=['events.view_event'],
        category='Événements',
        format_type='pdf'
    ),
    
    # ========================================
    # CULTE (LIENS VERS PAGES EXISTANTES)
    # ========================================
    'worship_services': ExportConfig(
        name='Services de Culte',
        description='Accéder aux feuilles de route et planifications',
        icon='bi-music-note-beamed',
        url_name='worship:service_list',
        permissions=['worship.view_worshipservice'],
        category='Culte',
        format_type='pdf'
    ),
}


def get_exports_by_category():
    """Retourne les exports groupés par catégorie."""
    categories = {}
    
    for export_key, export_config in EXPORT_REGISTRY.items():
        category = export_config.category
        if category not in categories:
            categories[category] = []
        categories[category].append((export_key, export_config))
    
    return categories


def get_user_exports(user):
    """Retourne les exports accessibles pour un utilisateur."""
    user_exports = {}
    
    for export_key, export_config in EXPORT_REGISTRY.items():
        if export_config.has_permission(user):
            category = export_config.category
            if category not in user_exports:
                user_exports[category] = []
            user_exports[category].append((export_key, export_config))
    
    return user_exports


def get_export_stats():
    """Retourne les statistiques des exports."""
    total = len(EXPORT_REGISTRY)
    by_format = {}
    by_category = {}
    sensitive_count = 0
    
    for export_config in EXPORT_REGISTRY.values():
        # Par format
        format_type = export_config.format_type
        by_format[format_type] = by_format.get(format_type, 0) + 1
        
        # Par catégorie
        category = export_config.category
        by_category[category] = by_category.get(category, 0) + 1
        
        # Sensibles
        if export_config.sensitive:
            sensitive_count += 1
    
    return {
        'total': total,
        'by_format': by_format,
        'by_category': by_category,
        'sensitive_count': sensitive_count
    }