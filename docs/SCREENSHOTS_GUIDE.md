# 📸 Guide des Captures d'Écran - Gestion des Logs Emails

## Où Placer les Screenshots

Tous les screenshots doivent être placés dans le dossier:
```
docs/screenshots/
```

## 📹 Screenshots à Capturer

Utilisez les noms de fichier exacts ci-dessous pour que les images s'intègrent correctement:

### 1. Interface Web

#### 📧 email-logs-main-interface.png
**Description:** Vue d'ensemble complète de l'interface

**À capturer:**
- Barre de navigation supérieure
- Tableau de bord statistique (4 cartes)
- Panneau de filtrage
- Tableau principal avec logs
- Cases à cocher
- Bouton Delete
- Pagination

**Instructions:**
1. Accédez à `/communication/logs/email/manage/`
2. Assurez-vous d'avoir au moins 10 logs
3. Prenez une screenshot de toute la page
4. Redimensionnez à max 1200px de large
5. Format: PNG
6. Enregistrez sous: `email-logs-main-interface.png`

---

#### 📊 dashboard-stats.png
**Description:** Tableau de bord statistique en détail

**À capturer:**
- 4 cartes de statistiques (Total, Sent, Failed, Pending)
- Icônes et nombre

**Instructions:**
1. Accédez à `/communication/logs/email/manage/`
2. Scrollez up pour voir les cartes
3. Prendre une screenshot des 4 cartes
4. Enregistrez sous: `dashboard-stats.png`

---

#### 🔍 filtering-panel.png
**Description:** Panneau de recherche et filtrage

**À capturer:**
- Boîte de recherche
- Dropdown de statut avec options ouvert
- Bouton Reset

**Instructions:**
1. Cliquez sur le dropdown Statut
2. Prenez une screenshot montrant l'ouverture
3. Enregistrez sous: `filtering-panel.png`

---

#### 📋 main-table.png
**Description:** Tableau principal avec logs

**À capturer:**
- 5-10 rows du tableau
- Headers visibles
- Cases à cocher
- Statuts avec couleurs
- Boutons Actions

**Instructions:**
1. Prenez une screenshot du tableau
2. Assurez-vous de montrer plusieurs statuts
3. Enregistrez sous: `main-table.png`

---

#### ☑️ select-all-checkbox.png
**Description:** Fonctionnalité "Select All"

**À capturer:**
- Case "Select All" dans l'en-tête
- Plusieurs cases cochées
- Bouton Delete activé
- Compteur de sélections

**Instructions:**
1. Cliquez "Select All"
2. Prenez une screenshot
3. Montrez le message "X selected"
4. Enregistrez sous: `select-all-checkbox.png`

---

#### 🗑️ delete-confirmation-modal.png
**Description:** Modal de confirmation avant suppression

**À capturer:**
- Modal dialog
- Liste des logs à supprimer
- Boutons Annuler/Confirmer
- Message d'avertissement

**Instructions:**
1. Sélectionnez 3 logs
2. Cliquez Delete
3. Prenez une screenshot du modal avant confirmation
4. Enregistrez sous: `delete-confirmation-modal.png`

---

#### 👁️ log-detail-modal.png
**Description:** Modal affichant les détails d'un log

**À capturer:**
- Informations du logs
- Sujet et contenu
- Statut et timestamps
- Messages d'erreur (si applicable)

**Instructions:**
1. Cliquez View sur un log
2. Prenez une screenshot du modal
3. Enregistrez sous: `log-detail-modal.png`

---

#### 📄 pagination-controls.png
**Description:** Contrôles de pagination en bas

**À capturer:**
- Boutons First, Previous, Page Numbers, Next, Last
- Affichage "Montrant X-Y de Z"

**Instructions:**
1. Scrollez en bas de la page
2. Prenez une screenshot de la pagination
3. Enregistrez sous: `pagination-controls.png`

---

### 2. Commande CLI

#### 🖥️ cli-command-execution.png
**Description:** Exécution normale de la commande

**À capturer:**
```
$ python manage.py delete_email_logs_interactive

📧 LOGS EMAILS DISPONIBLES POUR SUPPRESSION
================================================================================
  1. [17/02/2026 14:32] user1@example.com | Status: sent | ...
  2. [17/02/2026 10:15] user2@example.com | Status: failed | ...
  3. [17/02/2026 09:45] user3@example.com | Status: pending | ...
```

**Instructions:**
1. Exécutez la commande
2. Prenez une screenshot du résultat
3. Enregistrez sous: `cli-command-execution.png`

---

#### ❓ cli-selection-prompt.png
**Description:** Prompt de sélection interactif

**À capturer:**
```
👉 Entrez les numéros à supprimer: [input]
```

**Instructions:**
1. Exécutez la commande et attendez le prompt
2. Prenez une screenshot
3. Enregistrez sous: `cli-selection-prompt.png`

---

#### ✅ cli-confirmation-success.png
**Description:** Confirmation et résultat de suppression

**À capturer:**
```
✅ 3 log(s) supprimé(s) avec succès!
📊 Logs restants: 251
✨ Opération terminée!
```

**Instructions:**
1. Complétez une suppression
2. Prenez une screenshot du résultat
3. Enregistrez sous: `cli-confirmation-success.png`

---

#### 🔍 cli-dry-run-mode.png
**Description:** Exécution en mode dry-run

**À capturer:**
```
🔍 Mode dry-run: aucune suppression.
```

**Instructions:**
1. Exécutez: `python manage.py delete_email_logs_interactive --dry-run`
2. Prenez une screenshot
3. Enregistrez sous: `cli-dry-run-mode.png`

---

## 📐 Recommandations Techniques

### Dimensions
- **Largeur maximale:** 1200px
- **Format:** PNG ou WebP
- **Compression:** Activée

### Qualité
- **Résolution:** 1x (web standard) ou 2x (Retina)
- **DPI minimum:** 72 DPI
- **Couleurs:** RGB ou RGBA

### Optimisation
```bash
# Compresser les images (Linux/Mac)
convert image.png -quality 85 -strip image-compressed.png

# Ou avec imagemagick
mogrify -quality 85 -strip images/*.png

# Ou avec optipng
optipng -o2 image.png
```

### Accessibilité
Chaque image doit avoir un texte alt descriptif dans le guide:
```markdown
![Interface principale montrant le tableau de bord, 
   les filtres et la liste des logs avec cases à cocher]
(./screenshots/email-logs-main-interface.png)
```

---

## 🎨 Annotations (Optionnel)

Pour les captures complexes, vous pouvez ajouter des annotations:

| Outil | Platform | Gratuit |
|-------|----------|---------|
| **SnagIt** | Windows/Mac | ❌ |
| **Greenshot** | Windows | ✅ |
| **Annotate** | Windows | ✅ |
| **Screenshot Path** | Mac | ✅ |
| **GIMP** | Multi | ✅ |

### Exemple d'Annotations à Ajouter
- Flèches pointant vers éléments clés
- Boîtes autour des éléments importants
- Numéros (1, 2, 3) pour les étapes
- Texte explicatif court

---

## 📝 Structure du Dossier

```
docs/
├── screenshots/
│   ├── email-logs-main-interface.png
│   ├── dashboard-stats.png
│   ├── filtering-panel.png
│   ├── main-table.png
│   ├── select-all-checkbox.png
│   ├── delete-confirmation-modal.png
│   ├── log-detail-modal.png
│   ├── pagination-controls.png
│   ├── cli-command-execution.png
│   ├── cli-selection-prompt.png
│   ├── cli-confirmation-success.png
│   ├── cli-dry-run-mode.png
│   └── README.md (ce fichier)
├── EMAIL_LOGS_MANAGEMENT_GUIDE.md
├── EMAIL_LOGS_IMPLEMENTATION_SUMMARY.md
└── ... (autres docs)
```

---

## ✅ Checklist de Capture

### Interface Web
- [ ] email-logs-main-interface.png
- [ ] dashboard-stats.png
- [ ] filtering-panel.png
- [ ] main-table.png
- [ ] select-all-checkbox.png
- [ ] delete-confirmation-modal.png
- [ ] log-detail-modal.png
- [ ] pagination-controls.png

### Commande CLI
- [ ] cli-command-execution.png
- [ ] cli-selection-prompt.png
- [ ] cli-confirmation-success.png
- [ ] cli-dry-run-mode.png

---

## 📱 Responsive Design

L'interface doit être testée sur:
- ✅ Desktop (1920x1080)
- ✅ Tablet (768x1024)
- ✅ Mobile (375x667)

Priez les screenshots en **Desktop** par défaut.

---

## 🎯 Instructions Complètes pour Capturer

### Une Seule Fois
```bash
# 1. Créer le dossier screenshots
mkdir -p docs/screenshots

# 2. Prendre les screenshots selon le guide ci-dessus
# 3. Placer chaque screenshot avec le bon nom

# 4. Valider que les chemins dans le guide sont corrects
# 5. Tester que le markdown génère les bonnes images
```

### Commande pour Vérifier les Images
```bash
# Lister tous les fichiers
ls -la docs/screenshots/

# Vérifier les dimensions
identify docs/screenshots/*.png

# Vérifier la taille des fichiers
du -sh docs/screenshots/*
```

---

## 📄 Markdown pour Intégrer les Images

Dans le guide, les images sont intégrées comme ceci:

```markdown
> 📷 **Screenshot**: Voir `screenshots/email-logs-main-interface.png`

<!-- Ou avec lien direct: -->
![Interface principale](./screenshots/email-logs-main-interface.png)
```

---

## ⚡ Astuce Rapide

Si vous utilisez **VS Code**, vous pouvez faire des commentaires rapides:

```python
# Click Settings → Show Screenshot
# Puis Cmd/Ctrl + Shift + P → Take Screenshot
```

Ou utilisez **PowerShell** pour capturer écran:
```powershell
# Prendre une screenshot
$screen = [System.Windows.Forms.Screen]::AllScreens[0]
$bitmap = New-Object System.Drawing.Bitmap($screen.Bounds.Width, $screen.Bounds.Height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($screen.Bounds.Location, [System.Drawing.Point]::Empty, $screen.Bounds.Size)
$bitmap.Save("screenshot.png")
```

---

<div align="center">

**Dernière mise à jour:** 17 Février 2026  
**Guide Version:** 1.0

[Retour au Guide Principal](./EMAIL_LOGS_MANAGEMENT_GUIDE.md)

</div>
