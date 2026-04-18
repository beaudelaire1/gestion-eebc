# Import Excel Finance

L'import finance accepte un classeur Excel structure par onglets.

## Utilisation dans l'application

1. Ouvrir la tresorerie.
2. Cliquer sur Importer Excel.
3. Telecharger le modele fourni.
4. Remplir uniquement les onglets utiles.
5. Revenir sur la page d'import et charger le fichier.
6. Cocher Simulation uniquement pour verifier sans enregistrer.

## Utilisation en ligne de commande

```bash
python manage.py import_finance_excel chemin/vers/mon_fichier.xlsx
python manage.py import_finance_excel chemin/vers/mon_fichier.xlsx --dry-run
```

## Onglets pris en charge

- finance_categories
- budget_categories
- budget_lines
- budgets
- budget_items
- budget_requests
- forecasts
- forecast_lines
- transactions

## Regles importantes

- Conserver les noms d'onglets du modele.
- Conserver les entetes de colonnes du modele.
- Une meme ligne ne doit jamais contenir a la fois group_name et department_name.
- La feuille budget_items exige la feuille budgets.
- La feuille forecast_lines exige la feuille forecasts.
- Pour une transaction liee a un budget, renseigner budget_name, budget_year et budget_category_name.
- Pour une transaction liee a un evenement, renseigner event_title et event_start_date.

## Formats attendus

- Dates: YYYY-MM-DD
- Date/heure: YYYY-MM-DDTHH:MM:SS
- Booleens: TRUE/FALSE, oui/non, 1/0
- Montants: nombres decimaux sans symbole monetaire

## Conseils

- Commencer par une simulation.
- Importer d'abord les categories si le classeur introduit de nouveaux libelles.
- Importer ensuite les budgets, previsionnels et transactions.