# WhatsApp Cloud API — mise en service depuis zéro

Dernière mise à jour : 1er septembre 2026

Cette procédure part d'un compte Meta vierge. Elle couvre la création de l'app, du compte
WhatsApp Business, l'enregistrement du numéro, le modèle de message et le raccordement à
l'application EEBC.

Les écrans Meta changent régulièrement ; les noms de menus donnés ici peuvent différer
légèrement. La logique, elle, est stable.

## 0. Ce que fait l'application

L'envoi WhatsApp est déclenché par la **publication d'une annonce**, jamais par la tâche
quotidienne `run_notifications` qui, elle, n'envoie que des emails.

Chaque destinataire est un membre :

- au statut `ACTIF` ;
- dont `notify_by_whatsapp` est activé ;
- dont `whatsapp_number` est renseigné.

Toute tentative, réussie ou non, est journalisée dans la table `communication_smslog` avec le
message d'erreur brut renvoyé par Meta. C'est le premier endroit où regarder en cas de problème.

Le code appelle l'API Meta Cloud directement, sans SDK
([apps/communication/multichannel.py](../apps/communication/multichannel.py)). Un second chemin
historique passant par Twilio existe dans `notification_service.py` : il n'est configuré nulle
part et n'est pas utilisé.

## 1. Choisir le numéro de téléphone

C'est le seul prérequis réellement bloquant, et il se décide avant tout le reste.

Le numéro doit :

- pouvoir recevoir un **SMS ou un appel vocal** de vérification ;
- **ne pas être actif** sur WhatsApp ni sur WhatsApp Business (l'application mobile). Un numéro
  déjà utilisé doit d'abord être supprimé de ces applications, ce qui efface son historique de
  conversations ;
- rester dédié : une fois enregistré dans la Cloud API, il n'est plus utilisable dans
  l'application mobile WhatsApp.

Une ligne fixe convient : la vérification par appel vocal fonctionne.

Le **numéro de test** fourni par Meta dans *Getting Started* ne convient pas en production : il
ne peut écrire qu'à cinq destinataires pré-enregistrés.

## 2. Créer l'app Meta

Sur [developers.facebook.com](https://developers.facebook.com) :

1. **Mes apps → Créer une app** ;
2. type **Entreprise** ;
3. rattacher l'app au portefeuille Meta Business de l'église ;
4. dans les produits, ajouter **WhatsApp**.

Meta propose alors de créer un **compte WhatsApp Business (WABA)**. L'accepter.

Distinguer les trois objets, ils ne se suppriment pas de la même façon :

| Objet | Contient | Suppression |
|---|---|---|
| App | tokens, webhook, app secret | sans conséquence durable |
| WABA | numéros et **modèles approuvés** | fait perdre les approbations |
| Numéro | rattaché à un seul WABA | re-vérification nécessaire |

Pour repartir d'apps abandonnées : créer d'abord la nouvelle app et la rattacher au WABA
existant, **puis** supprimer les anciennes. Jamais l'inverse.

## 3. Enregistrer le numéro

Dans **WhatsApp → Configuration de l'API** :

1. **Ajouter un numéro de téléphone** ;
2. renseigner le nom affiché de l'organisation — il sera soumis à validation ;
3. vérifier par SMS ou appel ;
4. définir un **code PIN à 6 chiffres**. Le noter : il est exigé pour toute opération ultérieure
   sur le numéro, notamment un changement de WABA.

Relever le **Phone number ID** affiché : c'est lui, et non le numéro, qui va dans la
configuration.

## 4. Créer le modèle de message

Meta interdit tout message proactif hors modèle approuvé. Sans modèle, aucune annonce ne part.

Dans **WhatsApp Manager → Modèles de message → Créer un modèle** :

- **Catégorie** : *Marketing*. Une annonce d'église n'est pas transactionnelle ; un modèle
  *Utilitaire* utilisé pour ce contenu se fait rejeter ;
- **Nom** : par exemple `eebc_annonce`, en minuscules et sans espaces ;
- **Langue** : Français ;
- **Corps** : exactement trois variables, dans cet ordre.

```text
Bonjour {{1}},

{{2}}

{{3}}

EEBC
```

| Variable | Contenu envoyé par le code |
|---|---|
| `{{1}}` | nom complet du destinataire |
| `{{2}}` | titre de l'annonce |
| `{{3}}` | contenu de l'annonce, converti en texte brut |

Cet ordre est imposé par
[multichannel.py](../apps/communication/multichannel.py) : le modifier casse l'envoi.

L'approbation prend de quelques minutes à 24 heures.

## 5. Générer un token permanent

Le token affiché dans *Getting Started* **expire au bout de 24 heures**. Il ne convient pas.

Sur [business.facebook.com/settings](https://business.facebook.com/settings) :

1. **Utilisateurs → Utilisateurs système → Ajouter** ;
2. nommer l'utilisateur, rôle **Admin** ;
3. **Ajouter des actifs** → onglet **Comptes WhatsApp** → sélectionner le WABA → **Contrôle
   total** ;
4. **Générer un nouveau token** ;
5. choisir l'app créée à l'étape 2 ;
6. cocher `whatsapp_business_messaging` et `whatsapp_business_management` ;
7. expiration : **Jamais** ;
8. copier le token, il n'est affiché qu'une seule fois.

## 6. Configurer le webhook

Dans l'app → **WhatsApp → Configuration → Webhook** :

```text
URL de rappel   : https://eglise-ebc.org/webhooks/whatsapp/
Token de vérif. : la valeur de META_WHATSAPP_VERIFY_TOKEN
```

Le token de vérification est choisi librement, mais doit être identique des deux côtés.
S'abonner ensuite au champ `messages`.

Le webhook sert aux accusés de réception et aux réponses entrantes. L'envoi fonctionne sans lui,
mais les statuts de livraison ne remontent pas.

## 7. Renseigner l'application

Variables d'environnement Coolify :

```text
META_WHATSAPP_ACCESS_TOKEN=<token permanent, étape 5>
META_WHATSAPP_PHONE_NUMBER_ID=<Phone number ID, étape 3>
META_WHATSAPP_APP_SECRET=<app secret, propre à chaque app>
META_WHATSAPP_VERIFY_TOKEN=<valeur libre, identique au webhook>
META_WHATSAPP_API_VERSION=v23.0
META_WHATSAPP_ANNOUNCEMENT_TEMPLATE=<nom du modèle, étape 4>
META_WHATSAPP_TEMPLATE_LANGUAGE=fr
```

Ces sept variables sont déclarées dans `docker-compose.coolify.yml`. Le bloc `environment` étant
une liste blanche, **une variable absente de ce fichier n'atteint jamais le conteneur**, même
définie dans l'interface Coolify.

Redéployer ensuite : les variables ne sont injectées qu'à la création des conteneurs.

## 8. Vérifier

Token valide et numéro opérationnel :

```bash
docker exec -i <CONTENEUR_WEB> python - <<'PY'
import os, urllib.request, urllib.error

v = os.environ['META_WHATSAPP_API_VERSION']
pid = os.environ['META_WHATSAPP_PHONE_NUMBER_ID']
tok = os.environ['META_WHATSAPP_ACCESS_TOKEN']

req = urllib.request.Request(
    f'https://graph.facebook.com/{v}/{pid}?fields=display_phone_number,verified_name',
    headers={'Authorization': f'Bearer {tok}'},
)
try:
    print(urllib.request.urlopen(req, timeout=15).read().decode())
except urllib.error.HTTPError as exc:
    print('HTTP', exc.code)
    print(exc.read().decode())
PY
```

`verified_name` doit afficher le nom de l'église. `Test Number` signifie que le numéro de test
est encore configuré.

Puis publier une annonce dont on est le seul destinataire éligible, et lire le journal :

```bash
docker exec -i <CONTENEUR_WEB> python manage.py shell -c "from apps.communication.models import SMSLog; [print(l.status, l.recipient_phone, l.error_message or 'OK') for l in SMSLog.objects.order_by('-id')[:5]]"
```

## 9. Limites et erreurs courantes

Un WABA récent démarre avec un plafond de l'ordre de **250 conversations initiées par
24 heures**. C'est suffisant pour un envoi ponctuel à quelques centaines de membres, mais le
plafond exact et les paliers évoluent : les vérifier dans WhatsApp Manager avant un envoi de
masse. La **vérification d'entreprise** par Meta — qui exige les documents légaux de
l'association — est nécessaire pour monter en volume.

| Erreur | Signification |
|---|---|
| `190` / sous-code `463` | token expiré : c'est le token temporaire de 24 h |
| `190` / sous-code `467` | token révoqué, souvent après rotation de l'app secret |
| `100` | le Phone number ID n'appartient pas à l'app du token |
| `131047` | message hors fenêtre de 24 h envoyé sans modèle approuvé |
| `132001` | nom de modèle ou langue introuvable |
| `Meta WhatsApp non configuré` | token ou Phone number ID vide côté serveur |

Les numéros des membres sont normalisés en E.164 par
`WhatsAppMetaService._normalize_phone` : un numéro commençant par `0` est préfixé `+594`
(Guyane). Un membre joignable sur un indicatif étranger doit être saisi au format international.
