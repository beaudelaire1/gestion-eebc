"""
Bonnes pratiques d'optimisation pour le projet EEBC.
À lire absolument avant de coder !
"""

# ==================================================================================
# 🚀 OPTIMISATION DES REQUÊTES BD - BONNES PRATIQUES
# ==================================================================================

"""
1. TOUJOURS utiliser select_related() et prefetch_related()
   =========================================================
   
   ❌ MAUVAIS:
   members = Member.objects.all()  # N requêtes !
   for member in members:
       print(member.site.name)  # 1 requête par membre (N+1 problem)
   
   ✅ BON:
   from apps.core.optimization import get_optimized_queryset
   members = Member.objects.all()
   members = get_optimized_queryset('Member', members)
   
   ✅ MANUEL:
   members = Member.objects.select_related('site', 'department').all()


2. LIMITER les résultats avec [:limit]
   ==================================
   
   ❌ MAUVAIS:
   recent_events = request.user.events.all()  # Charge TOUS les événements !
   
   ✅ BON:
   recent_events = request.user.events.all()[:10]


3. UTILISER les indexes sur les requêtes fréquentes
   ===============================================
   
   Créer des indexes sur:
   - Champs utilisés dans les filtres (status, date, etc.)
   - Champs utilisés dans les recherches (email, username, etc.)
   - Champs de tri (created_at, etc.)
   
   L'appli contient une migration d'indexes :
   apps/core/migrations/0002_add_performance_indexes.py


4. CACHER les résultats coûteux
   ===========================
   
   ❌ MAUVAIS:
   def get_dashboard_stats(request):
       stats = expensive_calculation()
       return stats
   
   ✅ BON:
   from apps.core.optimization import cache_result, CacheConfig
   
   @cache_result(timeout=CacheConfig.LONG)
   def get_dashboard_stats(request):
       stats = expensive_calculation()
       return stats


5. UTILISER les agrégations et annotations
   ======================================
   
   ❌ MAUVAIS:
   total = 0
   for member in Member.objects.all():
       total += member.visits_received.count()  # 1 requête par membre !
   
   ✅ BON:
   from django.db.models import Count
   members_with_counts = Member.objects.annotate(
       visit_count=Count('visits_received')
   )
   total = sum(m.visit_count for m in members_with_counts)


6. PAGINER les listes longues
   =========================
   
   ❌ MAUVAIS:
   members = Member.objects.all()  # Charger 1000+ objets en mémoire
   
   ✅ BON:
   from django.core.paginator import Paginator
   paginator = Paginator(Member.objects.all(), 25)
   page = paginator.get_page(page_number)


7. BULK OPERATIONS pour les modifications en masse
   ============================================
   
   ❌ MAUVAIS:
   for member in Member.objects.all():
       member.status = 'actif'
       member.save()  # 1 requête par ligne !
   
   ✅ BON:
   Member.objects.all().update(status='actif')  # 1 requête seulement


8. UTILISER only() et defer() pour les grands champs
   ===============================================
   
   ❌ MAUVAIS:
   images = Child.objects.all()  # Charger les BLOBs de photos !
   
   ✅ BON:
   images = Child.objects.defer('photo', 'description').all()


9. ÉVITER les requêtes dans les templates
   =====================================
   
   ❌ MAUVAIS dans template:
   {% for member in members %}
       {% for visit in member.visits_received.all %}  <!-- Requête par ligne! -->
   
   ✅ BON dans le template (données pré-chargées):
   {% for member in members_with_visits %}
       {% for visit in member.visits %}


10. PROFILER avant d'optimiser
    ========================
    
    Utiliser django-debug-toolbar en développement:
    - pip install django-debug-toolbar
    - Voir les requêtes SQL et leur temps d'exécution
    - Identifier les vrai goulots d'étranglement


CONFIGURATION CACHING
====================

Dans settings/base.py:
- REDIS_URL : Si disponible, le cache utilisera Redis (plus rapide)
- Sinon : Cache en mémoire locale (LocMemCache)

Cache timeouts prédéfinis:
from apps.core.optimization import CacheConfig

- CacheConfig.SHORT (60s) : Données temps réel
- CacheConfig.MEDIUM (5m) : Listes
- CacheConfig.LONG (30m) : Statistiques
- CacheConfig.VERY_LONG (1h) : Données stables
- CacheConfig.DAY (24h) : Config/lookups


IMPORTS UTILES
==============

from apps.core.optimization import (
    cache_result,
    CacheConfig,
    get_optimized_queryset,
    OPTIMIZATION_CONFIGS,
    log_queries,
)

from django.db.models import (
    Q,  # Recherches complexes
    Count, Sum, Avg,  # Aggrégations
    F,  # Opérations sur champs
    Case, When,  # Requêtes conditionnelles
    Prefetch,  # Contrôle fin de prefetch_related
)


MIGRATION DE PERFORMANCE
========================

Run: python manage.py migrate core

Cela applesque tous les indexes critiques pour:
- members.Member
- events.Event
- finance.FinancialTransaction
- bibleclub.Child
- accounts.User
- communication.Notification


VÉRIFIER LES PERFS
==================

1. Django Debug Toolbar (dev uniquement):
   - Voir les requêtes SQL
   - Voir les N+1 problems
   - Voir les temps de requête

2. Utiliser @log_queries sur les vues suspectes:
   from apps.core.optimization import log_queries
   
   @log_queries
   def my_view(request):
       ...

3. Tester en production avec des données réelles
   - psql pour PostgreSQL
   - EXPLAIN ANALYZE pour analyser les requêtes


SUIVI DES PROGRÈS
=================

✅ indexes ajoutés sur les champs critiques
✅ select_related/prefetch_related dans member_list
✅ Cache configuration en place
⏳ Application systématique à toutes les vues (phase 5)
⏳ Profiling et rasterisation (phase 5 bis)
⏳ Tests de charge (phase 6)


QUESTIONS ?
===========

Vérifi les imports sur places avant de douoter de la config.
Utilise get_python_environment_details pour vérifier les dépendances.
"""

# Ce fichier est documentaire - pas de code à exécuter
