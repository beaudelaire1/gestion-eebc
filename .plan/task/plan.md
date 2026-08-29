# Plan de travail - Campagnes mobile/QR sécurisé

Date: 2026-04-03

## Objectif critique
Permettre la participation à une campagne depuis un téléphone avec:
- lien partageable,
- QR code,
- tunnel de don sécurisé,
- rattachement du don à la campagne.

## Audit existant
- Don public déjà disponible via `/don/` (Stripe) mais non relié aux campagnes.
- Dons campagne internes réservés aux utilisateurs connectés (`/app/campaigns/.../donate/`).
- Pas de lien public campagne ni QR code dans le back-office campagne.

## Décisions
1. Utiliser un token signé (`django.core.signing`) pour éviter exposition brute et falsification de l'ID campagne.
2. Générer un lien public mobile depuis le détail campagne.
3. Générer un QR code de ce lien public dans le détail campagne.
4. Préremplir la campagne dans la page de don public via token.
5. Propager `campaign_id` dans les metadata Stripe pour rattacher automatiquement les dons confirmés à la campagne.

## Implémentation
- `apps/campaigns/views.py`: ajout lien public signé + URL QR code dans `campaign_detail`.
- `templates/campaigns/campaign_detail.html`: bloc partage mobile (copie lien + QR).
- `apps/finance/donation_views.py`: lecture/validation du token campagne côté page et côté création session.
- `templates/finance/donation_page.html`: affichage campagne ciblée + transmission token.
- `apps/finance/stripe_service.py`: metadata `campaign_id`, création automatique d'un `campaigns.Donation` à la confirmation paiement.

## Risques
- Service QR externe indisponible: le lien reste copiable et partageable.
- Webhook Stripe en échec partiel sur rattachement campagne: transaction financière reste créée, warning loggé.

## Validation prévue
- Vérifier compilation Django et tests ciblés campagnes/finance.
- Vérifier navigation: détail campagne -> lien public -> page don préremplie.
- Vérifier metadata Stripe inclut `campaign_id`.

## Statut
- Implémentation: en cours
- Validation: à exécuter
