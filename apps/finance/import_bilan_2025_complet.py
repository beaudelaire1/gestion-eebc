"""
Script d'import COMPLET du bilan EEBC 2025 vers le prévisionnel budgétaire.
Extrait les données des 3 feuilles du classeur BILAN EEBC 2025.xlsx :
    1. BILAN FONCTIONNEL - Recettes/dépenses mensuelles réelles
    2. RESULTAT - Soldes et fonds spéciaux
    3. BILAN PREVISIONNEL - Budget prévisionnel annuel

Usage recommandé : python manage.py import_budget_forecasts_2025
Usage alternatif : python manage.py shell -c "exec(open('apps/finance/import_bilan_2025_complet.py', encoding='utf-8').read())"
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_eebc.settings')

from calendar import monthrange
from datetime import date
from decimal import Decimal
from django.utils import timezone

from apps.finance.models import BudgetForecast, FinanceCategory, FinancialTransaction, ForecastLine
from django.contrib.auth import get_user_model

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()

MONTH_KEYS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
              'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
IMPORT_MARKER = '[IMPORT BILAN 2025]'
OPERATING_INCOME_PARENT = 'Recettes de fonctionnement'
OPERATING_EXPENSE_PARENT = 'Dépenses de fonctionnement'
DEDICATED_FUNDS_PARENT = 'Fonds dédiés'
MONTH_LABELS = {
    'jan': 'janvier',
    'feb': 'février',
    'mar': 'mars',
    'apr': 'avril',
    'may': 'mai',
    'jun': 'juin',
    'jul': 'juillet',
    'aug': 'août',
    'sep': 'septembre',
    'oct': 'octobre',
    'nov': 'novembre',
    'dec': 'décembre',
}


def distribute_annual(total):
    monthly = (total / 12).quantize(Decimal('0.01'))
    remainder = total - monthly * 12
    months = {k: monthly for k in MONTH_KEYS}
    months['dec'] += remainder
    return months


def distribute_prorata(total, profile):
    total_profile = sum(profile.values())
    if total_profile == 0:
        return distribute_annual(total)
    months = {k: (v / total_profile * total).quantize(Decimal('0.01')) for k, v in profile.items()}
    diff = total - sum(months.values())
    months['dec'] += diff
    return months


def create_line(forecast, label, line_type, monthly_data):
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


def get_or_create_category(name, is_income, parent_name=None):
    parent = None
    if parent_name:
        parent, _ = FinanceCategory.objects.get_or_create(
            name=parent_name,
            defaults={
                'description': 'Catégorie parente créée automatiquement lors de l\'import du bilan EEBC 2025.',
                'is_income': is_income,
                'is_active': True,
            },
        )

    category, created = FinanceCategory.objects.get_or_create(
        name=name,
        defaults={
            'description': 'Catégorie créée automatiquement lors de l\'import du bilan EEBC 2025.',
            'is_income': is_income,
            'parent': parent,
            'is_active': True,
        },
    )

    fields_to_update = []
    if not category.is_active:
        category.is_active = True
        fields_to_update.append('is_active')
    if not category.description:
        category.description = 'Catégorie créée automatiquement lors de l\'import du bilan EEBC 2025.'
        fields_to_update.append('description')
    if created is False and category.is_income != is_income and category.transactions.exists() is False:
        category.is_income = is_income
        fields_to_update.append('is_income')
    if category.parent_id != (parent.id if parent else None):
        category.parent = parent
        fields_to_update.append('parent')

    if fields_to_update:
        category.save(update_fields=fields_to_update)

    return category


def last_day_of_month(year, month):
    return date(year, month, monthrange(year, month)[1])


def create_import_transaction(label, transaction_type, amount, transaction_date, category_name=None, description=None, notes='', parent_name=None):
    is_income = transaction_type in {
        FinancialTransaction.TransactionType.DON,
        FinancialTransaction.TransactionType.DIME,
        FinancialTransaction.TransactionType.OFFRANDE,
    }
    category = get_or_create_category(
        category_name or label,
        is_income=is_income,
        parent_name=parent_name,
    )
    return FinancialTransaction.objects.create(
        amount=amount,
        transaction_type=transaction_type,
        payment_method=FinancialTransaction.PaymentMethod.AUTRE,
        status=FinancialTransaction.Status.VALIDE,
        transaction_date=transaction_date,
        description=description or label,
        category=category,
        recorded_by=admin_user,
        validated_by=admin_user,
        validated_at=timezone.now(),
        notes=f"{IMPORT_MARKER} {notes}".strip(),
    )


# =========================================================================
# FEUILLE 1 : BILAN FONCTIONNEL - Données mensuelles réelles
# =========================================================================

# Offrandes mensuelles (colonne I gauche, N droite - lignes totaux)
OFFRANDES_MENSUELLES = {
    'jan': Decimal('2080.80'), 'feb': Decimal('1468.03'),
    'mar': Decimal('2002.88'), 'apr': Decimal('2019.83'),
    'may': Decimal('1691.45'), 'jun': Decimal('1943.80'),
    'jul': Decimal('3150.68'), 'aug': Decimal('1415.44'),
    'sep': Decimal('1660.09'), 'oct': Decimal('3171.22'),
    'nov': Decimal('2212.68'), 'dec': Decimal('2580.24'),
}  # Total: 25 397,14 €

# Dîmes mensuelles (colonne J gauche, O droite - lignes totaux)
DIMES_MENSUELLES = {
    'jan': Decimal('1200.00'), 'feb': Decimal('2800.00'),
    'mar': Decimal('1765.00'), 'apr': Decimal('1202.00'),
    'may': Decimal('2618.00'), 'jun': Decimal('2840.00'),
    'jul': Decimal('2123.00'), 'aug': Decimal('1260.00'),
    'sep': Decimal('3390.00'), 'oct': Decimal('1020.00'),
    'nov': Decimal('1981.00'), 'dec': Decimal('1370.00'),
}  # Total: 23 569,00 €

# Dépenses annuelles réelles (colonne A/C, lignes 25-51)
DEPENSES_REALISEES = [
    ("Produits d'entretien / Sainte Cène", Decimal('380.00')),
    ("EDF - Électricité", Decimal('1060.65')),
    ("SGDE - Eau", Decimal('180.25')),
    ("Frais de tenue de compte bancaire", Decimal('401.08')),
    ("Salaire du Pasteur", Decimal('15443.50')),
    ("CGSS Guyane - URSSAF", Decimal('4148.00')),
    ("AG2R - Retraite complémentaire", Decimal('3273.52')),
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
]  # Total: 42 704,19 €

# Recettes supplémentaires réelles (hors offrandes/dîmes)
RECETTES_DIVERSES_REALISEES = [
    ("Don pour un frère parti en étude", Decimal('1008.00')),
    ("Vente Bibles", Decimal('826.00')),
]  # Total: 1 834,00 €

# =========================================================================
# FEUILLE 2 : RESULTAT - Fonds spéciaux et soldes
# =========================================================================

SOLDE_31_12_2024 = Decimal('14306.90')

FONDS_SPECIAUX = [
    ("Caisse de fonctionnement au 31/12/2025", Decimal('8095.95')),
    ("Don Mana", Decimal('19800.00')),
    ("Fond pour chaises", Decimal('7000.00')),
    ("Don Sono", Decimal('4700.00')),
]  # Total: 39 595,95 €

SOLDE_BANQUE_31_12_2025 = Decimal('39595.95')

# Charges en attente (mentionnées feuille RESULTAT)
CHARGES_EN_ATTENTE = [
    "Salaire novembre - décembre",
    "Cotisation Fédération",
    "Méga briel (chaises)",
    "Loyer Macouria",
]

# =========================================================================
# FEUILLE 3 : BILAN PREVISIONNEL - Budget prévisionnel
# =========================================================================

DEPENSES_PREVISIONNELLES = [
    ("Eau", Decimal('350.00')),
    ("Électricité", Decimal('2800.00')),
    ("Orange - Télécom", Decimal('1100.00')),
    ("Produits d'entretien / Sainte Cène", Decimal('500.00')),
    ("Salaire du Pasteur", Decimal('16200.00')),
    ("Cotisation Fédération Baptiste", Decimal('2500.00')),
    ("Fourniture matériel (sonorisation)", Decimal('15000.00')),
    ("Sécurité de l'Église", Decimal('0.00')),  # Pas de montant en D11
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
]  # Total: 80 410,00 €

RECETTES_PREVISIONNELLES = [
    ("Offrandes", Decimal('31500.00')),
    ("Dîmes", Decimal('32410.00')),
    ("Dons divers Mana", Decimal('16500.00')),
]  # Total: 80 410,00 €

# Données historiques 2013 (colonnes B/C feuille BILAN PREVISIONNEL)
HISTORIQUE_2013 = {
    'depenses': {
        "Eau": Decimal('1200.00'),
        "Électricité": Decimal('700.00'),
        "Orange": Decimal('250.00'),
        "Produits d'entretien": Decimal('500.00'),
        "Salaires pasteur": Decimal('250.00'),
        "Cotisation fédération": Decimal('1250.00'),
        "Sonorisation": Decimal('1250.00'),
        "Sécurité Église": Decimal('2500.00'),
        "Charges sociales": Decimal('1800.00'),
        "Services bancaires": Decimal('1000.00'),
        "Mise aux normes": Decimal('1000.00'),
        "Extincteurs": Decimal('4680.00'),
        "Dons divers": Decimal('400.00'),
        "Assurances": Decimal('300.00'),
        "The Ray Of Sunshine": Decimal('300.00'),
        "Dons humanitaire": Decimal('150.00'),
        "Aide Mana": Decimal('500.00'),
    },
    'recettes': {
        "Offrandes": Decimal('16500.00'),
        "Dîmes": Decimal('23400.00'),
    },
    'total_depenses': Decimal('18030.00'),
    'total_recettes': Decimal('39900.00'),
}


# =========================================================================
# CRÉATION DES PRÉVISIONNELS
# =========================================================================

print("=" * 70)
print("IMPORT COMPLET DU BILAN EEBC 2025 (3 feuilles)")
print("=" * 70)

# Supprimer les anciens prévisionnels 2025 pour repartir propre
deleted = BudgetForecast.objects.filter(year=2025).delete()
print(f"\nNettoyage: {deleted[0]} objets supprimés")

deleted_transactions = FinancialTransaction.all_objects.filter(
    transaction_date__year=2025,
    notes__startswith=IMPORT_MARKER,
).delete()
print(f"Nettoyage trésorerie: {deleted_transactions[0]} transaction(s) importée(s) supprimée(s)")


# ─────────────────────────────────────────────
# 1) PRÉVISIONNEL 2025 - Scénario RÉALISTE
# ─────────────────────────────────────────────
print("\n" + "─" * 70)
print("1. PRÉVISIONNEL 2025 (Réaliste) — Feuille BILAN PREVISIONNEL")
print("─" * 70)

f_prev = BudgetForecast.objects.create(
    name="Budget prévisionnel 2025",
    year=2025,
    scenario='realiste',
    description=(
        "Budget prévisionnel de l'Église pour 2025.\n"
        "Source : feuille « BILAN PREVISIONNEL » du classeur BILAN EEBC 2025.\n"
        "Recettes prévisionnelles distribuées au prorata du profil mensuel réel.\n"
        f"Budget équilibré à 80 410 €.\n"
        f"Données historiques 2013 disponibles pour comparaison."
    ),
    created_by=admin_user,
    is_active=True,
)

# Recettes : distribuées au prorata des mois réels
for label, total in RECETTES_PREVISIONNELLES:
    if label == 'Offrandes':
        monthly = distribute_prorata(total, OFFRANDES_MENSUELLES)
    elif label == 'Dîmes':
        monthly = distribute_prorata(total, DIMES_MENSUELLES)
    else:
        monthly = distribute_annual(total)
    create_line(f_prev, label, 'income', monthly)
    print(f"  [RECETTE]  {label}: {total:>10} €")

# Dépenses prévisionnelles
for label, total in DEPENSES_PREVISIONNELLES:
    if total > 0:
        monthly = distribute_annual(total)
        create_line(f_prev, label, 'expense', monthly)
        print(f"  [DEPENSE]  {label}: {total:>10} €")

total_r = sum(t for _, t in RECETTES_PREVISIONNELLES)
total_d = sum(t for _, t in DEPENSES_PREVISIONNELLES)
print(f"\n  Total recettes: {total_r:>12} €")
print(f"  Total dépenses: {total_d:>12} €")
print(f"  Solde net:      {total_r - total_d:>12} €")
print(f"  → {f_prev.lines.count()} lignes créées")


# ─────────────────────────────────────────────
# 2) BILAN RÉALISÉ 2025 - Scénario RÉALISÉ
# ─────────────────────────────────────────────
print("\n" + "─" * 70)
print("2. BILAN RÉALISÉ 2025 (Réalisé) — Feuilles BILAN FONCTIONNEL + RESULTAT")
print("─" * 70)

f_reel = BudgetForecast.objects.create(
    name="Bilan réalisé 2025 (données comptables)",
    year=2025,
    scenario='realise',
    description=(
        "Données réelles de l'exercice 2025.\n"
        "Source : feuilles « BILAN FONCTIONNEL » et « RESULTAT ».\n\n"
        f"Solde au 31/12/2024 : {SOLDE_31_12_2024} €\n"
        f"Solde en banque au 31/12/2025 : {SOLDE_BANQUE_31_12_2025} €\n\n"
        "Fonds spéciaux au 31/12/2025 :\n"
        + "\n".join(f"  • {label} : {montant} €" for label, montant in FONDS_SPECIAUX)
        + "\n\nCharges en attente :\n"
        + "\n".join(f"  • {c}" for c in CHARGES_EN_ATTENTE)
    ),
    created_by=admin_user,
    is_active=True,
)

# Recettes mensuelles réelles détaillées
create_line(f_reel, 'Offrandes', 'income', OFFRANDES_MENSUELLES)
print(f"  [RECETTE]  Offrandes (mensuel détaillé): {sum(OFFRANDES_MENSUELLES.values()):>10} €")

create_line(f_reel, 'Dîmes', 'income', DIMES_MENSUELLES)
print(f"  [RECETTE]  Dîmes (mensuel détaillé):     {sum(DIMES_MENSUELLES.values()):>10} €")

# Recettes diverses
for label, total in RECETTES_DIVERSES_REALISEES:
    monthly = distribute_annual(total)
    create_line(f_reel, label, 'income', monthly)
    print(f"  [RECETTE]  {label}: {total:>10} €")

# Fonds spéciaux (Don Mana, Sono, Chaises)
# NOTE : les fonds spéciaux ne sont PAS ajoutés aux recettes du bilan
# fonctionnel pour ne pas gonfler les recettes de fonctionnement.
# Ils sont documentés dans la description et gérés séparément.
# for label, total in FONDS_SPECIAUX:
#     if label != "Caisse de fonctionnement au 31/12/2025":
#         monthly = distribute_annual(total)
#         create_line(f_reel, label, 'income', monthly)
#         print(f"  [FONDS]    {label}: {total:>10} €")

# Dépenses réelles
for label, total in DEPENSES_REALISEES:
    monthly = distribute_annual(total)
    create_line(f_reel, label, 'expense', monthly)

total_recettes_reel = (
    sum(OFFRANDES_MENSUELLES.values())
    + sum(DIMES_MENSUELLES.values())
    + sum(t for _, t in RECETTES_DIVERSES_REALISEES)
)
total_dep_reel = sum(t for _, t in DEPENSES_REALISEES)

print(f"\n  Total recettes (incl. fonds): {total_recettes_reel:>12} €")
print(f"  Total dépenses:               {total_dep_reel:>12} €")
print(f"  Résultat:                      {total_recettes_reel - total_dep_reel:>12} €")
print(f"  → {f_reel.lines.count()} lignes créées")


# ─────────────────────────────────────────────
# 2bis) TRÉSORERIE 2025 - Transactions réelles importées
# ─────────────────────────────────────────────
print("\n" + "─" * 70)
print("2bis. TRÉSORERIE 2025 — Alimentation des transactions validées")
print("─" * 70)

imported_transaction_count = 0
imported_income_total = Decimal('0.00')
imported_expense_total = Decimal('0.00')

for month_index, month_key in enumerate(MONTH_KEYS, start=1):
    transaction_date = last_day_of_month(2025, month_index)
    month_label = MONTH_LABELS[month_key]

    offrandes_amount = OFFRANDES_MENSUELLES[month_key]
    if offrandes_amount > 0:
        create_import_transaction(
            label='Offrandes',
            transaction_type=FinancialTransaction.TransactionType.OFFRANDE,
            amount=offrandes_amount,
            transaction_date=transaction_date,
            description=f"Offrandes agrégées — {month_label} 2025",
            notes=f"Flux mensuel importé depuis le bilan fonctionnel ({month_label} 2025).",
            parent_name=OPERATING_INCOME_PARENT,
        )
        imported_transaction_count += 1
        imported_income_total += offrandes_amount

    dimes_amount = DIMES_MENSUELLES[month_key]
    if dimes_amount > 0:
        create_import_transaction(
            label='Dîmes',
            transaction_type=FinancialTransaction.TransactionType.DIME,
            amount=dimes_amount,
            transaction_date=transaction_date,
            description=f"Dîmes agrégées — {month_label} 2025",
            notes=f"Flux mensuel importé depuis le bilan fonctionnel ({month_label} 2025).",
            parent_name=OPERATING_INCOME_PARENT,
        )
        imported_transaction_count += 1
        imported_income_total += dimes_amount

annual_import_date = date(2025, 12, 31)

for label, total in RECETTES_DIVERSES_REALISEES:
    create_import_transaction(
        label=label,
        transaction_type=FinancialTransaction.TransactionType.DON,
        amount=total,
        transaction_date=annual_import_date,
        description=f"{label} — import annuel 2025",
        notes='Recette diverse agrégée importée depuis le bilan 2025.',
        parent_name=OPERATING_INCOME_PARENT,
    )
    imported_transaction_count += 1
    imported_income_total += total

for label, total in FONDS_SPECIAUX:
    if label == "Caisse de fonctionnement au 31/12/2025":
        continue

    create_import_transaction(
        label=label,
        transaction_type=FinancialTransaction.TransactionType.DON,
        amount=total,
        transaction_date=annual_import_date,
        description=f"{label} — fonds spécial importé 2025",
        notes='Fonds spécial importé depuis la feuille RESULTAT 2025.',
        parent_name=DEDICATED_FUNDS_PARENT,
    )
    imported_transaction_count += 1
    imported_income_total += total

for label, total in DEPENSES_REALISEES:
    create_import_transaction(
        label=label,
        transaction_type=FinancialTransaction.TransactionType.DEPENSE,
        amount=total,
        transaction_date=annual_import_date,
        description=f"{label} — charge agrégée 2025",
        notes='Dépense annuelle agrégée importée depuis le bilan 2025.',
        parent_name=OPERATING_EXPENSE_PARENT,
    )
    imported_transaction_count += 1
    imported_expense_total += total

print(f"  Transactions importées:       {imported_transaction_count:>12}")
print(f"  Total entrées importées:      {imported_income_total:>12} €")
print(f"  Total sorties importées:      {imported_expense_total:>12} €")
print("  Note: la caisse de fonctionnement au 31/12/2025 reste un solde, pas un flux importable.")


# ─────────────────────────────────────────────
# 3) SCÉNARIO PESSIMISTE (basé sur historique 2013)
# ─────────────────────────────────────────────
print("\n" + "─" * 70)
print("3. PRÉVISIONNEL 2025 (Pessimiste) — Basé sur données 2013")
print("─" * 70)

f_pess = BudgetForecast.objects.create(
    name="Scénario pessimiste 2025 (base 2013)",
    year=2025,
    scenario='pessimiste',
    description=(
        "Scénario pessimiste basé sur les données historiques de 2013.\n"
        "Source : colonnes B/C de la feuille « BILAN PREVISIONNEL ».\n"
        "Permet de visualiser un scénario de recettes minimales."
    ),
    created_by=admin_user,
    is_active=True,
)

for label, total in HISTORIQUE_2013['recettes'].items():
    monthly = distribute_annual(total)
    create_line(f_pess, label, 'income', monthly)
    print(f"  [RECETTE]  {label}: {total:>10} €")

for label, total in HISTORIQUE_2013['depenses'].items():
    monthly = distribute_annual(total)
    create_line(f_pess, label, 'expense', monthly)
    print(f"  [DEPENSE]  {label}: {total:>10} €")

total_r_pess = sum(HISTORIQUE_2013['recettes'].values())
total_d_pess = sum(HISTORIQUE_2013['depenses'].values())
print(f"\n  Total recettes: {total_r_pess:>12} €")
print(f"  Total dépenses: {total_d_pess:>12} €")
print(f"  Solde net:      {total_r_pess - total_d_pess:>12} €")
print(f"  → {f_pess.lines.count()} lignes créées")


# ─────────────────────────────────────────────
# RÉCAPITULATIF FINAL
# ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("IMPORT TERMINÉ — RÉCAPITULATIF")
print("=" * 70)
print(f"  1. Réaliste  — {f_prev.lines.count():>3} lignes — Budget prévu : {total_r} € / {total_d} €")
print(f"  2. Réalisé   — {f_reel.lines.count():>3} lignes — Réel : {total_recettes_reel} € / {total_dep_reel} €")
print(f"  3. Pessimiste— {f_pess.lines.count():>3} lignes — Historique 2013 : {total_r_pess} € / {total_d_pess} €")
print(f"  4. Trésorerie — {imported_transaction_count:>3} transactions — Flux : {imported_income_total} € / {imported_expense_total} €")
print(f"\n  Solde en banque au 31/12/2024 : {SOLDE_31_12_2024} €")
print(f"  Solde en banque au 31/12/2025 : {SOLDE_BANQUE_31_12_2025} €")
print(f"  Fonds spéciaux : {sum(t for _, t in FONDS_SPECIAUX)} €")
print("=" * 70)
