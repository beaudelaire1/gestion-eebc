"""
Script d'import du bilan EEBC 2025 vers le prévisionnel budgétaire.
Usage: python manage.py shell < apps/finance/import_bilan_2025.py
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')

from decimal import Decimal
from apps.finance.models import BudgetForecast, ForecastLine
from django.contrib.auth import get_user_model

User = get_user_model()

# Récupérer un admin pour le created_by
admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

# =============================================
# DONNÉES EXTRAITES DU BILAN EEBC 2025
# =============================================

# Recettes mensuelles (BILAN FONCTIONNEL)
OFFRANDES_MENSUELLES = {
    'jan': Decimal('2080.80'),
    'feb': Decimal('1468.03'),
    'mar': Decimal('2002.88'),
    'apr': Decimal('2019.83'),
    'may': Decimal('1691.45'),
    'jun': Decimal('1943.80'),
    'jul': Decimal('3150.68'),
    'aug': Decimal('1415.44'),
    'sep': Decimal('1660.09'),
    'oct': Decimal('3171.22'),
    'nov': Decimal('2212.68'),
    'dec': Decimal('2580.24'),
}

DIMES_MENSUELLES = {
    'jan': Decimal('1200.00'),
    'feb': Decimal('2800.00'),
    'mar': Decimal('1765.00'),
    'apr': Decimal('1202.00'),
    'may': Decimal('2618.00'),
    'jun': Decimal('2840.00'),
    'jul': Decimal('2123.00'),
    'aug': Decimal('1260.00'),
    'sep': Decimal('3390.00'),
    'oct': Decimal('1020.00'),
    'nov': Decimal('1981.00'),
    'dec': Decimal('1370.00'),
}

# Dépenses annuelles (BILAN FONCTIONNEL - réalisées)
DEPENSES_REALISEES = [
    ("Produits d'entretien / Sainte Cène", Decimal('380.00')),
    ("EDF - Électricité", Decimal('1060.65')),
    ("SGDE - Eau", Decimal('180.25')),
    ("Frais de tenue de compte", Decimal('401.08')),
    ("Salaire du Pasteur", Decimal('15443.50')),
    ("CGSS Guyane - URSSAF", Decimal('4148.00')),
    ("AG2R - Retraite", Decimal('3273.52')),
    ("Loyer Macouria", Decimal('2000.00')),
    ("Orange - Télécom", Decimal('1020.00')),
    ("Chéry Dieula", Decimal('450.00')),
    ("Groupama Assurance", Decimal('2461.24')),
    ("Fête de fin d'année", Decimal('600.00')),
    ("LC Location", Decimal('387.00')),
    ("Cours de chant", Decimal('180.00')),
    ("Club biblique", Decimal('2500.00')),
    ("Achat chaises", Decimal('99.00')),
    ("Don remis au frère (études)", Decimal('1008.00')),
    ("Chrono Clim - Climatisation", Decimal('2470.00')),
    ("Groupe de jeunes", Decimal('300.00')),
    ("Crique Coco - Sortie", Decimal('500.00')),
    ("Guyanaise Distribution", Decimal('1172.07')),
    ("Musique et Son - Sono", Decimal('2226.00')),
    ("Dons enterrement Edna", Decimal('400.00')),
    ("Hyper U - Divers", Decimal('17.67')),
    ("Gifi - Divers", Decimal('26.21')),
]

# Dépenses prévisionnelles (BILAN PREVISIONNEL)
DEPENSES_PREVISIONNELLES = [
    ("Eau", Decimal('350.00')),
    ("Électricité", Decimal('2800.00')),
    ("Orange - Télécom", Decimal('1100.00')),
    ("Produits d'entretien / Sainte Cène", Decimal('500.00')),
    ("Salaire du Pasteur", Decimal('16200.00')),
    ("Cotisation Fédération Baptiste", Decimal('2500.00')),
    ("Fourniture matériel (sonorisation)", Decimal('15000.00')),
    ("Charges sociales", Decimal('4500.00')),
    ("Services bancaires", Decimal('500.00')),
    ("Matériel de bureau", Decimal('2000.00')),
    ("Mise aux normes électricité", Decimal('3000.00')),
    ("Extincteurs", Decimal('2960.00')),
    ("Dons divers", Decimal('2000.00')),
    ("Assurances", Decimal('2800.00')),
    ("Club biblique", Decimal('3000.00')),
    ("La Jeunesse", Decimal('1000.00')),
    ("The Ray Of Sunshine", Decimal('200.00')),
    ("Dons humanitaire", Decimal('3500.00')),
    ("Aide Mana", Decimal('16500.00')),
]

RECETTES_PREVISIONNELLES = {
    'Offrandes': Decimal('31500.00'),
    'Dîmes': Decimal('32410.00'),
    'Dons divers Mana': Decimal('16500.00'),
}

MONTH_KEYS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
              'jul', 'aug', 'sep', 'oct', 'nov', 'dec']


def distribute_annual(total):
    """Distribue un montant annuel uniformément sur 12 mois."""
    monthly = (total / 12).quantize(Decimal('0.01'))
    remainder = total - monthly * 12
    months = {k: monthly for k in MONTH_KEYS}
    months['dec'] += remainder  # ajuster le dernier mois
    return months


def create_forecast_line(forecast, label, line_type, monthly_data):
    """Crée une ForecastLine avec les montants mensuels."""
    ForecastLine.objects.create(
        forecast=forecast,
        label=label,
        line_type=line_type,
        jan=monthly_data.get('jan', 0),
        feb=monthly_data.get('feb', 0),
        mar=monthly_data.get('mar', 0),
        apr=monthly_data.get('apr', 0),
        may=monthly_data.get('may', 0),
        jun=monthly_data.get('jun', 0),
        jul=monthly_data.get('jul', 0),
        aug=monthly_data.get('aug', 0),
        sep=monthly_data.get('sep', 0),
        oct=monthly_data.get('oct', 0),
        nov=monthly_data.get('nov', 0),
        dec=monthly_data.get('dec', 0),
    )


# =============================================
# 1) PRÉVISIONNEL 2025 (scénario réaliste)
# =============================================
print("=" * 60)
print("IMPORT DU BILAN EEBC 2025")
print("=" * 60)

forecast_prev, created = BudgetForecast.objects.get_or_create(
    year=2025,
    scenario='realiste',
    defaults={
        'name': 'Budget prévisionnel 2025',
        'description': "Budget prévisionnel de l'Église pour 2025 (importé du fichier Excel BILAN EEBC 2025)",
        'created_by': admin_user,
        'is_active': True,
    }
)
if not created:
    forecast_prev.lines.all().delete()
    print(f"  -> Prévisionnel réaliste 2025 existant, lignes réinitialisées.")
else:
    print(f"  -> Prévisionnel réaliste 2025 créé.")

# Recettes prévisionnelles (distribuer les totaux annuels avec le profil mensuel réel)
total_offrandes_reel = sum(OFFRANDES_MENSUELLES.values())
total_dimes_reel = sum(DIMES_MENSUELLES.values())

# Offrandes : distribuer 31500€ au prorata des offrandes mensuelles réelles
for label_prev, total_prev in RECETTES_PREVISIONNELLES.items():
    if label_prev == 'Offrandes':
        monthly = {k: (v / total_offrandes_reel * total_prev).quantize(Decimal('0.01'))
                   for k, v in OFFRANDES_MENSUELLES.items()}
    elif label_prev == 'Dîmes':
        monthly = {k: (v / total_dimes_reel * total_prev).quantize(Decimal('0.01'))
                   for k, v in DIMES_MENSUELLES.items()}
    else:
        monthly = distribute_annual(total_prev)
    
    create_forecast_line(forecast_prev, label_prev, 'income', monthly)
    print(f"  [RECETTE] {label_prev}: {total_prev} €")

# Dépenses prévisionnelles (distribuées uniformément sur 12 mois)
for label_dep, total_dep in DEPENSES_PREVISIONNELLES:
    monthly = distribute_annual(total_dep)
    create_forecast_line(forecast_prev, label_dep, 'expense', monthly)
    print(f"  [DEPENSE] {label_dep}: {total_dep} €")

total_r = sum(RECETTES_PREVISIONNELLES.values())
total_d = sum(t for _, t in DEPENSES_PREVISIONNELLES)
print(f"\n  Total recettes prévisionnelles: {total_r} €")
print(f"  Total dépenses prévisionnelles: {total_d} €")
print(f"  Solde prévisionnel: {total_r - total_d} €")

# =============================================
# 2) BILAN RÉALISÉ 2025 (scénario pour comparaison)
# =============================================
forecast_reel, created = BudgetForecast.objects.get_or_create(
    year=2025,
    scenario='optimiste',
    defaults={
        'name': 'Bilan réalisé 2025',
        'description': "Données réelles de l'exercice 2025 (importées du fichier Excel BILAN EEBC 2025)",
        'created_by': admin_user,
        'is_active': True,
    }
)
if not created:
    forecast_reel.lines.all().delete()
    print(f"\n  -> Bilan réalisé 2025 existant, lignes réinitialisées.")
else:
    print(f"\n  -> Bilan réalisé 2025 créé.")

# Recettes mensuelles réelles
create_forecast_line(forecast_reel, 'Offrandes', 'income', OFFRANDES_MENSUELLES)
print(f"  [RECETTE] Offrandes: {sum(OFFRANDES_MENSUELLES.values())} €")

create_forecast_line(forecast_reel, 'Dîmes', 'income', DIMES_MENSUELLES)
print(f"  [RECETTE] Dîmes: {sum(DIMES_MENSUELLES.values())} €")

# Dépenses réelles (distribuées uniformément - pas de détail mensuel dans l'Excel)
for label_dep, total_dep in DEPENSES_REALISEES:
    monthly = distribute_annual(total_dep)
    create_forecast_line(forecast_reel, label_dep, 'expense', monthly)

total_off = sum(OFFRANDES_MENSUELLES.values())
total_dim = sum(DIMES_MENSUELLES.values())
total_dep_reel = sum(t for _, t in DEPENSES_REALISEES)
print(f"\n  Total recettes réelles: {total_off + total_dim} €")
print(f"  Total dépenses réelles: {total_dep_reel} €")
print(f"  Résultat: {total_off + total_dim - total_dep_reel} €")

print("\n" + "=" * 60)
print("IMPORT TERMINÉ AVEC SUCCÈS")
print(f"  -> 2 prévisionnels créés pour 2025")
print(f"  -> Réaliste: {forecast_prev.lines.count()} lignes")
print(f"  -> Bilan réalisé: {forecast_reel.lines.count()} lignes")
print("=" * 60)
