---
description: "Auditer une zone du projet EEBC: securite, permissions, performance, tests et risques de production"
name: "Audit EEBC"
argument-hint: "Zone a auditer, ex. apps/finance, API mobile, imports ou documents"
agent: "agent"
---

Réalise un audit read-only du périmètre demandé. Ne modifie aucun fichier sauf si l'utilisateur le demande explicitement après l'audit.

## Contexte À Charger
- Instructions projet : [AGENTS.md](../../AGENTS.md).
- Architecture : [ARCHITECTURE.md](../../ARCHITECTURE.md).
- Checklist production : [PRODUCTION_CHECKLIST.md](../../PRODUCTION_CHECKLIST.md).
- Checklist audit : [.skill/.gemini/context/audit-checklist.md](../../.skill/.gemini/context/audit-checklist.md).
- Checklist sécurité : [.skill/.codex/skills/atlas-prime/references/security-checklist.md](../../.skill/.codex/skills/atlas-prime/references/security-checklist.md).
- Template de rapport : [.skill/.codex/skills/atlas-prime/templates/audit-report.md](../../.skill/.codex/skills/atlas-prime/templates/audit-report.md).

## Méthode
1. Délimite le périmètre exact à partir de la demande et liste les fichiers lus.
2. Remonte les chemins d'entrée : URLs, vues, formulaires, serializers, modèles, tasks, signals, templates, webhooks et settings concernés.
3. Vérifie les risques sécurité : accès, rôles, IDOR, CSRF, XSS, injection, uploads, secrets, logs sensibles et exposition d'erreurs.
4. Vérifie les risques données et production : migrations, intégrations externes, Celery/Redis, email, Cloudinary, Stripe, Render, variables d'environnement.
5. Vérifie performance et maintenabilité : N+1, pagination, cache, duplication, couplage, dette de tests.
6. Compare avec les tests existants et recommande les validations minimales à lancer.

## Sortie Attendue
Présente les constats en premier, triés par gravité.

| Gravité | Emplacement | Risque | Preuve | Correction recommandée | Validation |
|---|---|---|---|---|---|

Puis ajoute seulement si utile :
- points forts réels ;
- questions ou hypothèses ;
- commandes de validation recommandées ;
- risques résiduels.
