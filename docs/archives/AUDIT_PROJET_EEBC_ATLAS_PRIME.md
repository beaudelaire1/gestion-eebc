# Audit Report — Gestion EEBC

> Protocole : ATLAS PRIME (.skill/.codex/skills/atlas-prime)  
> Date : Juillet 2025  
> Périmètre : intégralité du dépôt `eebc_project`

---

## 1. Lecture stratégique

- **Objet de l'audit** : évaluer la maturité technique, la posture de sécurité, la maintenabilité et la capacité de mise en production de l'application Django « Gestion EEBC » (gestion d'église).
- **Périmètre** : 17 apps Django sous `apps/`, 1 app orpheline `young/`, settings multi-environnements, CI/CD GitHub Actions, déploiement Render, API REST mobile.
- **Niveau de risque** : **élevé** — l'application manipule des données personnelles (membres, familles, adresses, données financières, reçus fiscaux), des paiements Stripe et des communications multicanales (email, SMS, WhatsApp).
- **Point de vigilance dominant** : l'écart entre les mécanismes de sécurité *déclarés* (CSP, rate limiting, audit) et ceux *réellement actifs* en production.

---

## 2. Contexte observé

- **Stack identifiée** :
  - Django 4.2.27, Python 3.11.4
  - Frontend : HTMX + Bootstrap 5 (crispy-bootstrap5), Jazzmin admin
  - API : Django REST Framework + SimpleJWT (app mobile Flutter `eebc_mobile/`)
  - Base de données : PostgreSQL (prod via Render), SQLite (dev/tests)
  - Services externes : Stripe (dons), Twilio (SMS/WhatsApp), Hostinger (emails), Sentry (erreurs)
  - Fichiers statiques : WhiteNoise, WeasyPrint (PDF)
  - CI/CD : GitHub Actions (3 workflows), déploiement Render (free tier)

- **Zones lues** (exhaustif) :
  - `gestion_eebc/settings/` (base, dev, prod, test)
  - `gestion_eebc/urls.py`
  - 17 apps : models, views, forms, services, urls, permissions, middleware, signals
  - `conftest.py`, `test_factories.py`, fichiers test_*.py racine
  - `.github/workflows/` (tests.yml, code-quality.yml)
  - `render.yaml`, `build.sh`, `start.sh`
  - `requirements/` (base.txt, prod.txt)
  - `young/` (app orpheline)

- **Conventions observées** :
  - Vues fonctionnelles avec décorateurs `@login_required` + `@role_required`
  - Pattern service layer dans 7/17 apps (accounts, core, finance, groups, imports, communication, bibleclub)
  - Custom User avec rôles stockés en texte CSV dans un champ unique
  - Formulaires via ModelForm + mixin HTML5ValidationMixin + FrenchErrorMessagesMixin
  - Audit logging via signals Django + AuditMiddleware (thread-local)

- **Hypothèses** :
  - L'application est en usage restreint (1 église, quelques sites paroissiaux)
  - Le free tier Render impose un seul worker/instance
  - Pas d'utilisation asynchrone Django (pas d'ASGI), donc le pattern thread-local est acceptable pour l'instant

---

## 3. Points forts réels

1. **Système RBAC bien pensé** — Le module `apps/core/permissions.py` implémente un décorateur `@role_required` propre, un mixin `RoleRequiredMixin`, une configuration `ROLE_PERMISSIONS` par module/action, et un logging systématique des accès refusés dans `AuditLog`.

2. **Audit logging complet** — `apps/core/signals.py` intercepte `pre_save`, `post_save`, `post_delete` sur les modèles critiques, les login/logout, et tag correctement les champs sensibles à exclure (password, two_factor_secret).

3. **Architecture modulaire propre** — 17 apps avec séparation claire des responsabilités (accounts, members, finance, worship, etc.), chaque app ayant son propre `urls.py`, `models.py`, `views.py`, `forms.py`.

4. **Exports sécurisés** — `apps/core/export_views.py` implémente un `ExportPermissionMixin` avec matrice de permissions par type d'export, logging des exports dans AuditLog, et gestion fine des rôles autorisés.

5. **Protection GPS des membres** — `apps/members/admin_views.py` obfusque les coordonnées GPS des membres pour les non-admins via un décalage déterministe (8-15m), protégeant la vie privée.

6. **Webhook Stripe avec vérification de signature** — `apps/finance/stripe_service.py` utilise `stripe.Webhook.construct_event()` pour valider les webhooks, ce qui est la bonne pratique.

7. **CI/CD multi-couche** — tests.yml (pytest + linting), code-quality.yml (Semgrep SAST, pylint, radon), déploiement automatique vers Render.

---

## 4. Problèmes identifiés

### Critiques

#### C1 — CSP déclaré mais non appliqué
- **Problème** : Les variables `CSP_DEFAULT_SRC`, `CSP_SCRIPT_SRC`, etc. sont définies dans `gestion_eebc/settings/base.py` (L158-177), mais le package `django-csp` n'est dans aucun fichier `requirements/*.txt` et aucun middleware CSP n'est dans `MIDDLEWARE`.
- **Impact** : Aucun en-tête Content-Security-Policy n'est envoyé. La protection XSS côté navigateur est absente.
- **Cause probable** : Configuration préparée mais dépendance jamais installée.
- **Correction prioritaire** : Ajouter `django-csp` à `requirements/base.txt`, ajouter `csp.middleware.CSPMiddleware` au `MIDDLEWARE`, remplacer `'unsafe-inline'` par des nonces HTMX.

#### C2 — profile_view : mise à jour sans validation de formulaire
- **Problème** : `apps/accounts/views.py` (L280-286) — `profile_view` écrit directement `request.POST.get()` dans les champs User sans aucune validation :
  ```python
  user.first_name = request.POST.get('first_name', '')
  user.last_name = request.POST.get('last_name', '')
  user.email = request.POST.get('email', '')
  user.phone = request.POST.get('phone', '')
  user.save()
  ```
- **Impact** : Pas de validation d'email (format, unicité), pas de validation téléphone, pas de longueur max — corruption de données possible, potentiel pour usurper l'email d'un autre utilisateur.
- **Cause probable** : Vue écrite rapidement sans formulaire dédié.
- **Correction prioritaire** : Créer un `ProfileForm(ModelForm)` avec les validations appropriées.

#### C3 — Endpoint de don public expose les exceptions internes
- **Problème** : `apps/finance/donation_views.py` (L99) — `CreateDonationSessionView.post()` retourne `str(e)` en cas d'exception :
  ```python
  except Exception as e:
      return JsonResponse({'error': str(e)}, status=400)
  ```
- **Impact** : Fuite d'informations internes (traces Stripe, chemins de fichiers, clés partielles) vers des utilisateurs non authentifiés. Cet endpoint est public.
- **Cause probable** : Gestion d'erreur de développement non remplacée.
- **Correction prioritaire** : Logger l'exception côté serveur, retourner un message générique au client.

#### C4 — Import de fichiers sans contrôle de rôle ni validation de fichier
- **Problème** : `apps/imports/views.py` (L64) — `import_create` utilise `@login_required` sans `@role_required`. N'importe quel utilisateur authentifié peut lancer un import Excel. Aucune validation du type de fichier (extension, magic bytes) ni de la taille.
- **Impact** : Un membre avec le rôle le plus bas peut importer des données dans la base. Fichier malveillant possible (zip bomb, formula injection Excel).
- **Cause probable** : Rôle manquant lors de l'implémentation.
- **Correction prioritaire** : Ajouter `@role_required('admin', 'secretariat')`, valider extension + taille + magic bytes du fichier uploadé.

#### C5 — Import via threading.Thread au lieu de Celery
- **Problème** : `apps/imports/views.py` (L79-83) — Le traitement d'import est lancé dans un `threading.Thread(daemon=True)`.
- **Impact** : Si le thread crash, aucune reprise possible, aucune notification, l'`ImportLog` reste en statut « en cours » indéfiniment. Sur Render free tier (1 worker), un import lourd bloque le serveur.
- **Cause probable** : Celery déclaré optionnel dans les dépendances mais jamais branché pour cette fonctionnalité.
- **Correction prioritaire** : Utiliser Celery (déjà dans requirements/prod.txt) ou a minima traiter de manière synchrone avec timeout.

### Importants

#### I1 — Tests CI utilisent SQLite mais provisionnent PostgreSQL
- **Problème** : `.github/workflows/tests.yml` déclare un service Postgres (L14-22), mais `gestion_eebc/settings/test.py` force SQLite en mémoire (L18-21). Le `DATABASE_URL` envoyé en env (L66) est ignoré.
- **Impact** : Les tests ne valident jamais le comportement PostgreSQL réel (contraintes, types, performances). Bugs spécifiques Postgres passent inaperçus.
- **Cause probable** : test.py écrit pour la rapidité locale, jamais mis à jour pour CI.
- **Correction recommandée** : Dans test.py, utiliser `DATABASE_URL` via `dj_database_url` si défini, sinon fallback SQLite.

#### I2 — safety check silencieux dans le CI
- **Problème** : `.github/workflows/tests.yml` (L100) — `safety check --json || true` masque toute vulnérabilité connue dans les dépendances.
- **Impact** : Des CVE critiques dans les dépendances passent sans bloquer le pipeline.
- **Correction recommandée** : Retirer `|| true`, configurer les exceptions dans un fichier `.safety-policy.yml`.

#### I3 — CAPTCHA fail-open en production
- **Problème** : `apps/accounts/views.py` — Si ni Turnstile ni reCAPTCHA ne sont configurés, la validation CAPTCHA est simplement ignorée (pas de reject explicite en production).
- **Impact** : Si les clés CAPTCHA sont perdues ou non configurées sur Render, les logins sont sans protection anti-bot.
- **Correction recommandée** : Approche fail-closed — si aucun CAPTCHA n'est configuré en production (`not DEBUG`), refuser la requête.

#### I4 — Formulaires publics sans CAPTCHA
- **Problème** : `apps/core/views.py` — `ContactView` et `VisitorRegistrationView` sont des `CreateView` publiques sans aucune protection CAPTCHA visible.
- **Impact** : Spam sur le formulaire de contact et fausses inscriptions de visiteurs.
- **Correction recommandée** : Ajouter Turnstile/reCAPTCHA sur ces formulaires.

#### I5 — Stripe crée un nouveau Product à chaque don récurrent
- **Problème** : `apps/finance/stripe_service.py` — `create_recurring_donation()` appelle `stripe.Product.create()` à chaque appel.
- **Impact** : Pollution du dashboard Stripe avec des Products identiques. Difficulté d'audit financier.
- **Correction recommandée** : Créer un Product une seule fois (ou le récupérer par metadata), réutiliser son ID.

#### I6 — Reçu fiscal avec données placeholder
- **Problème** : `apps/finance/pdf_service.py` (L33-34) — SIRET `"XXX XXX XXX XXXXX"` et RNA `"W9XXXXXXXX"` en dur.
- **Impact** : Si utilisé en production, les reçus fiscaux sont juridiquement invalides.
- **Correction recommandée** : Déplacer vers `SiteSettings` ou variables d'environnement, vérifier que les valeurs sont configurées avant de générer un reçu.

#### I7 — Module core surchargé (17 modèles)
- **Problème** : `apps/core/models.py` contient 17 modèles mélangeant : config site, géographie, familles, contenu public (news, pages, sliders, témoignages), audit, backups.
- **Impact** : Module fourre-tout difficile à maintenir, couplage élevé, migrations lourdes.
- **Correction recommandée** : Extraire le contenu public (NewsArticle, PageContent, Slider, Testimony, ContactMessage, VisitorRegistration, PublicEvent) vers `apps/public/models.py`.

#### I8 — Pas de tests pour les modules critiques
- **Problème** : Aucun fichier de tests dans `apps/finance/`, `apps/worship/`, `apps/events/`, `apps/groups/`.
- **Impact** : Les modules les plus sensibles (transactions financières, reçus fiscaux, assignations de rôles culte) n'ont aucune couverture de test.
- **Correction recommandée** : Priorité aux tests unitaires finance (calculs, reçus, Stripe) et worship (tokens UUID, expirations).

#### I9 — TODO en production : reçu fiscal sans pièce jointe PDF
- **Problème** : `apps/finance/models.py` (L793) — `# TODO: Ajouter la pièce jointe PDF` — l'email de reçu fiscal est envoyé sans le PDF.
- **Impact** : Les donateurs reçoivent un email de confirmation sans le document fiscal attendu.
- **Correction recommandée** : Attacher le PDF généré par `pdf_service.py` à l'email.

### Mineurs

#### M1 — App `young/` orpheline
- **Problème** : Le dossier `young/` à la racine contient une app Django vide (models.py = commentaire), non enregistrée dans `INSTALLED_APPS`, non référencée nulle part.
- **Impact** : Confusion pour les développeurs, dette technique.
- **Correction possible** : Supprimer le dossier ou l'intégrer à `apps/bibleclub/`.

#### M2 — Rôles stockés en texte CSV
- **Problème** : `apps/accounts/models.py` — les rôles utilisateur sont stockés dans un `TextField` en format CSV (`"pasteur,finance"`).
- **Impact** : Pas de relation M2M, pas de contrainte de base de données, parsing fragile, pas d'index possible sur un rôle spécifique.
- **Correction possible** : Migration vers un modèle `UserRole` M2M ou un `ArrayField` PostgreSQL.

#### M3 — Fichiers test_*.py à la racine
- **Problème** : 22 fichiers `test_*.py` à la racine du projet, certains utilisant `django.setup()` + `print()` plutôt que pytest.
- **Impact** : Tests non-conventionnels, difficilement exécutables dans le CI, confusion avec les vrais tests pytest.
- **Correction possible** : Migrer les tests vers les dossiers d'apps, formatter en pytest.

#### M4 — `docker build` silencieux dans le CI
- **Problème** : `.github/workflows/tests.yml` — l'étape `docker build . -t eebc:${{ github.sha }} || true` échoue silencieusement (pas de Dockerfile).
- **Impact** : Étape inutile qui masque un problème de configuration.
- **Correction possible** : Supprimer l'étape ou créer un Dockerfile.

#### M5 — Incrémentation de vues sans déduplication
- **Problème** : `apps/core/views.py` — `NewsDetailView` incrémente `views_count` à chaque GET, sans déduplication par session ou IP.
- **Impact** : Compteurs de vues gonflés artificiellement.
- **Correction possible** : Déduplication par session ou IP+date.

---

## 5. Analyse transversale

### Sécurité
- **Bien fait** : Authentification solide (CAPTCHA dual, 2FA TOTP, rate limiting login, tokens signés, audit des accès refusés), webhook Stripe avec signature, obfuscation GPS, HSTS en production.
- **Insuffisant** : CSP non appliqué (C1), fuite d'exception publique (C3), pas de CAPTCHA sur formulaires publics (I4), `profile_view` sans validation (C2), import sans contrôle d'accès (C4).
- **Risque résiduel** : Aucune analyse DPIA formelle malgré les données personnelles sensibles (RGPD applicable en Guyane française).

### Performance
- **Bien fait** : `select_related` utilisé dans les vues membres et finance, pagination configurée, cache Redis optionnel déclaré.
- **Insuffisant** : Import Excel en `threading.Thread` bloquant (C5), pas de cache Redis activé en free tier Render, `views_count` incrémenté en base à chaque page view (M5).
- **Risque résiduel** : Render free tier = 1 worker. Tout import lourd ou génération PDF bloque les requêtes concurrentes.

### Maintenabilité
- **Bien fait** : Architecture par apps, formulaires avec mixins, service layer dans 7 apps, conventions de nommage cohérentes.
- **Insuffisant** : core surchargé avec 17 modèles (I7), pas de service layer dans 9 apps, 22 fichiers test à la racine, duplication des patterns CRUD dans les vues fonctionnelles.
- **Risque résiduel** : Sans refactoring du core, chaque migration touchant ce module impacte potentiellement toute l'application.

### Accessibilité / UX
- **Bien fait** : Bootstrap 5 + crispy forms, messages d'erreur en français, validation HTML5 automatique via mixin.
- **Non évalué** : Accessibilité WCAG non auditée (hors périmètre code uniquement).

### Delivery / Ops
- **Bien fait** : render.yaml déclaratif, build.sh/start.sh documentés, health check configuré (`/healthz/ping/`), Sentry optionnel, déploiement auto sur push main.
- **Insuffisant** : Tests CI ne testent pas contre PostgreSQL réel (I1), `safety check` silencieux (I2), Semgrep ne bloque pas le pipeline (informational only), pas de Dockerfile, pas de staging environment.
- **Risque résiduel** : Déploiement direct main → production sans validation intermédiaire. Un merge cassant atterrit directement en production.

---

## 6. Priorisation recommandée

| # | Action | Criticité | Effort |
|---|--------|-----------|--------|
| 1 | **C2** — Créer `ProfileForm` et valider les entrées de `profile_view` | 🔴 Critique | Faible |
| 2 | **C3** — Remplacer `str(e)` par message générique dans `CreateDonationSessionView` | 🔴 Critique | Faible |
| 3 | **C4** — Ajouter `@role_required` + validation fichier sur `import_create` | 🔴 Critique | Faible |
| 4 | **C1** — Installer `django-csp`, activer le middleware, configurer les nonces | 🔴 Critique | Moyen |
| 5 | **C5** — Remplacer `threading.Thread` par Celery pour les imports | 🔴 Critique | Moyen |
| 6 | **I3/I4** — CAPTCHA fail-closed + CAPTCHA sur formulaires publics | 🟠 Important | Moyen |
| 7 | **I1** — Aligner test.py sur PostgreSQL en CI | 🟠 Important | Faible |
| 8 | **I2** — Retirer `|| true` sur safety check | 🟠 Important | Trivial |
| 9 | **I6** — Externaliser SIRET/RNA en variables d'environnement | 🟠 Important | Faible |
| 10 | **I8** — Écrire les tests finance et worship | 🟠 Important | Élevé |
| 11 | **I5** — Réutiliser le Stripe Product pour les dons récurrents | 🟡 Moyen | Faible |
| 12 | **I7** — Refactoring du module core (extraire modèles publics) | 🟡 Moyen | Élevé |
| 13 | **I9** — Attacher le PDF au mail de reçu fiscal | 🟡 Moyen | Moyen |
| 14 | **M1-M5** — Nettoyage : young/, tests racine, docker build, views_count | 🟢 Mineur | Variable |

---

## 7. Livraison

### Résumé exécutable
L'application Gestion EEBC présente une architecture Django solide et bien structurée avec de bons réflexes de sécurité (RBAC, audit, 2FA, rate limiting). Cependant, **5 problèmes critiques** doivent être corrigés avant toute mise en production avec des données réelles :

1. Le CSP est configuré mais non appliqué (absence de `django-csp`).
2. La vue profil permet une mise à jour sans validation de formulaire.
3. L'endpoint de donation expose les exceptions internes aux utilisateurs anonymes.
4. L'import de fichiers n'a ni contrôle de rôle ni validation de fichier.
5. L'import utilise `threading.Thread` au lieu de Celery.

Les corrections 1 à 4 sont réalisables en quelques heures chacune. La correction 5 nécessite la mise en place de Celery (ou une alternative synchrone).

### Risques résiduels
- **RGPD** : Aucune analyse DPIA, pas de mécanisme de droit à l'oubli, pas de registre de traitement documenté.
- **Stripe** : Le webhook est bien sécurisé, mais la gestion des Products récurrents pollue le dashboard Stripe.
- **Tests** : Les modules finance et worship (haute criticité) n'ont aucune couverture de tests.
- **Déploiement** : Pas de staging, pas de rollback automatisé, Render free tier = 1 worker.

### Ce qui n'a PAS été vérifié
- Templates HTML : vérification XSS partielle (Django autoescaping activé par défaut, mais pas d'inspection manuelle des templates).
- Sérialiseurs DRF : l'API mobile n'a pas été auditée en détail au niveau sérialisation.
- Celery tasks : déclarées dans certains services mais non testées (Celery non actif en free tier).
- Performance en charge : aucun load test réalisé.

### Étape suivante recommandée
1. Corriger C1-C4 (sécurité critique, effort faible).
2. Écrire une suite de tests minimale pour `apps/finance/` et `apps/worship/`.
3. Configurer un environnement staging sur Render avant d'exposer des données réelles.
