# Gestion EEBC - Guyane 🇬🇫

ERP minimaliste pour église en Guyane française - Club Biblique & Calendrier Intelligent

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Django](https://img.shields.io/badge/Django-4.2+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🎯 Fonctionnalités

### Club Biblique (Priorité)
- ✅ Gestion des tranches d'âge et classes
- ✅ Inscription et suivi des enfants
- ✅ Gestion des moniteurs
- ✅ Système d'appel par session
- ✅ Suivi des présences avec statistiques
- ✅ Gestion du transport enfants
- ✅ Notifications d'absences

### Calendrier Intelligent
- ✅ Vue calendrier FullCalendar
- ✅ Événements récurrents
- ✅ Visibilité publique/restreinte
- ✅ Catégorisation des événements

### Gestion Générale
- ✅ Membres de l'église
- ✅ Départements
- ✅ Groupes (Jeunesse, Chorale, etc.)
- ✅ Campagnes de collecte
- ✅ Inventaire du matériel
- ✅ Transport bénévole
- ✅ Système de notifications
- ✅ Tableau de bord avec alertes

## 🚀 Installation

### Prérequis
- Python 3.11+
- pip

### Étapes

1. **Cloner ou accéder au projet**
```bash
cd eebc_project
```

2. **Créer l'environnement virtuel**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Appliquer les migrations**
```bash
python manage.py makemigrations
python manage.py migrate
```

5. **Configurer le système avec les données de démo**
```bash
python manage.py setup_eebc
```

6. **Lancer le serveur**
```bash
python manage.py runserver
```

7. **Accéder à l'application**
- Application : http://127.0.0.1:8000
- Administration : http://127.0.0.1:8000/admin

## 🔐 Comptes Utilisateurs (TEMPORAIRES - DEV)

| Utilisateur | Mot de passe | Rôle |
|-------------|--------------|------|
| `admin` | `admin1234` | Administrateur |
| `responsable` | `club1234` | Responsable Club Biblique |
| `moniteur` | `moniteur1234` | Moniteur |
| `chauffeur` | `chauffeur1234` | Chauffeur |
| `resp_groupe` | `groupe1234` | Responsable de Groupe |
| `membre` | `user1234` | Membre |

⚠️ **ATTENTION** : Ces mots de passe sont TEMPORAIRES et destinés uniquement au développement. Changez-les impérativement en production !

## 📁 Structure du Projet

```
eebc_project/
├── gestion_eebc/          # Configuration Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/                   # Applications Django
│   ├── accounts/          # Authentification & Utilisateurs
│   ├── members/           # Gestion des membres
│   ├── departments/       # Départements de l'église
│   ├── transport/         # Transport bénévole
│   ├── inventory/         # Inventaire matériel
│   ├── campaigns/         # Campagnes de collecte
│   ├── bibleclub/         # Club Biblique ⭐
│   ├── events/            # Événements & Calendrier
│   ├── groups/            # Groupes (Jeunesse, Chorale...)
│   ├── communication/     # Notifications & Annonces
│   └── dashboard/         # Tableau de bord
├── templates/             # Templates HTML
├── static/                # Fichiers statiques
├── media/                 # Fichiers uploadés
└── manage.py
```

## 🛣️ Routes Principales

| URL | Description |
|-----|-------------|
| `/` | Tableau de bord |
| `/accounts/login/` | Connexion |
| `/bibleclub/` | Club Biblique |
| `/bibleclub/children/` | Liste des enfants |
| `/bibleclub/sessions/` | Sessions & Appels |
| `/events/calendar/` | Calendrier |
| `/members/` | Membres |
| `/groups/` | Groupes |
| `/campaigns/` | Campagnes |
| `/admin/` | Administration Django |

## 🎨 Interface

L'interface utilise :
- **Design** : Thème clair moderne
- **Charte graphique** :
  - Bleu primaire : `#0A36FF`
  - Blanc : `#FFFFFF`
  - Noir profond : `#0B0F19`
- **Framework CSS** : Bootstrap 5.3
- **Icônes** : Bootstrap Icons
- **Interactivité** : HTMX pour les mises à jour dynamiques
- **Calendrier** : FullCalendar 6
- **Typographie** : Poppins (Google Fonts)

## ⚙️ Configuration

### Variables d'environnement

Créez un fichier `.env` à la racine (optionnel) :

```env
DEBUG=True
SECRET_KEY=votre-cle-secrete
ALLOWED_HOSTS=localhost,127.0.0.1
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Base de données

SQLite par défaut (développement). Pour la production, configurez PostgreSQL ou MySQL dans `settings.py`.

## 📋 TODO Post-MVP

- [ ] Changement de mot de passe utilisateur
- [ ] Réinitialisation de mot de passe par email
- [ ] Export PDF des listes et rapports
- [ ] Intégration SMS (Twilio)
- [ ] Intégration WhatsApp Business API
- [ ] Application mobile (PWA)
- [ ] Synchronisation calendrier externe (Google, iCal)
- [ ] Statistiques avancées et graphiques
- [ ] Gestion des dons en ligne
- [ ] Multi-langue

## 🧪 Tests

```bash
python manage.py test
```

## 📄 Licence

MIT License - Libre d'utilisation et de modification.

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

---

Développé avec ❤️ pour EEBC Guyane 🇬🇫

