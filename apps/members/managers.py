"""
Managers personnalisés pour les modèles Member.
"""
from django.db import models
import random
import string


class MemberManager(models.Manager):
    """
    Manager personnalisé pour le modèle Member.
    Contient la logique de génération d'ID et les requêtes optimisées.
    """
    
    def generate_member_id(self, site=None):
        """
        Génère un ID unique au format EEBC-CAB-XXXX ou EEBC-MAC-XXXX.
        
        Args:
            site: Instance de Site (optionnel)
            
        Returns:
            str: ID membre unique
        """
        # Déterminer le code du site
        if site and hasattr(site, 'code') and site.code:
            site_code = site.code
        else:
            # Par défaut, Cabassou si pas de site défini
            site_code = 'CAB'
        
        # Générer un ID unique avec gestion atomique
        max_attempts = 100
        for _ in range(max_attempts):
            random_suffix = ''.join(random.choices(string.digits, k=4))
            new_id = f"EEBC-{site_code}-{random_suffix}"
            
            # Vérifier l'unicité de manière atomique
            if not self.filter(member_id=new_id).exists():
                return new_id
        
        # Fallback avec plus de chiffres si nécessaire
        random_suffix = ''.join(random.choices(string.digits, k=6))
        return f"EEBC-{site_code}-{random_suffix}"
    
    def with_visit_stats(self):
        """
        Retourne un QuerySet avec les statistiques de visites annotées.
        Évite les requêtes N+1 pour les propriétés calculées.
        """
        from django.db.models import Max, Count, Case, When, IntegerField
        from django.conf import settings
        from datetime import date, timedelta
        
        threshold_days = getattr(settings, 'MEMBER_VISIT_THRESHOLD_DAYS', 180)
        threshold_date = date.today() - timedelta(days=threshold_days)
        
        return self.annotate(
            last_visit_date_anno=Max('visits_received__visit_date'),
            total_visits=Count('visits_received'),
            recent_visits=Count(
                'visits_received',
                filter=models.Q(visits_received__visit_date__gte=threshold_date)
            ),
            needs_visit_anno=Case(
                When(last_visit_date_anno__isnull=True, then=1),
                When(last_visit_date_anno__lt=threshold_date, then=1),
                default=0,
                output_field=IntegerField()
            )
        )
    
    def with_life_events(self):
        """
        Retourne un QuerySet avec les événements de vie préchargés.
        """
        return self.prefetch_related(
            'life_events',
            'related_life_events'
        )
    
    def needing_visits(self):
        """
        Retourne les membres nécessitant une visite pastorale.
        """
        from django.conf import settings
        from datetime import date, timedelta
        
        threshold_days = getattr(settings, 'MEMBER_VISIT_THRESHOLD_DAYS', 180)
        threshold_date = date.today() - timedelta(days=threshold_days)
        
        return self.filter(
            models.Q(visits_received__isnull=True) |
            models.Q(visits_received__visit_date__lt=threshold_date)
        ).distinct()
    
    def active_members(self):
        """
        Retourne les membres actifs.
        """
        return self.filter(status='actif')
    
    def by_site(self, site):
        """
        Retourne les membres d'un site spécifique.
        """
        return self.filter(site=site)
    
    def with_contact_info(self):
        """
        Retourne les membres avec informations de contact complètes.
        """
        return self.exclude(
            models.Q(email='') & models.Q(phone='')
        )