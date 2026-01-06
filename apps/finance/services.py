"""
Service Layer pour le module Finance.

Ce module centralise la logique métier pour:
- La gestion des transactions financières (TransactionService)
- La gestion des budgets (BudgetService)

Requirements: 7.4
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, Any, List
from django.db.models import Sum, Q
from django.utils import timezone
from django.conf import settings

from .models import (
    FinancialTransaction, 
    FinanceCategory, 
    ReceiptProof,
    Budget, 
    BudgetItem, 
    BudgetCategory,
    BudgetRequest
)


class ServiceResult:
    """Résultat d'une opération de service."""
    
    def __init__(self, success: bool, data=None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
    
    @classmethod
    def ok(cls, data=None):
        return cls(success=True, data=data)
    
    @classmethod
    def fail(cls, error: str):
        return cls(success=False, error=error)


class TransactionService:
    """
    Service de gestion des transactions financières.
    
    Centralise la logique métier pour les opérations CRUD sur les transactions,
    les calculs de statistiques et la validation.
    """
    
    @classmethod
    def create_transaction(
        cls,
        data: Dict[str, Any],
        recorded_by,
        site=None
    ) -> ServiceResult:
        """
        Crée une nouvelle transaction financière.
        
        Args:
            data: Dictionnaire contenant les données de la transaction
                - transaction_type: Type de transaction (don, dime, offrande, depense, etc.)
                - amount: Montant de la transaction
                - transaction_date: Date de la transaction
                - payment_method: Méthode de paiement (optionnel)
                - category: Catégorie financière (optionnel)
                - description: Description (optionnel)
                - member: Membre concerné (optionnel)
                - event: Événement lié (optionnel)
                - notes: Notes internes (optionnel)
            recorded_by: Utilisateur qui enregistre la transaction
            site: Site d'appartenance (optionnel)
        
        Returns:
            ServiceResult avec data={'transaction': transaction} si succès
        """
        try:
            transaction = FinancialTransaction(
                transaction_type=data.get('transaction_type'),
                amount=Decimal(str(data.get('amount', 0))),
                transaction_date=data.get('transaction_date'),
                payment_method=data.get('payment_method', FinancialTransaction.PaymentMethod.ESPECES),
                category=data.get('category'),
                description=data.get('description', ''),
                member=data.get('member'),
                event=data.get('event'),
                notes=data.get('notes', ''),
                recorded_by=recorded_by,
                site=site,
                status=FinancialTransaction.Status.EN_ATTENTE
            )
            
            # La référence est générée automatiquement dans save()
            transaction.save()
            
            return ServiceResult.ok({'transaction': transaction})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de la création de la transaction: {str(e)}")
    
    @classmethod
    def update_transaction(
        cls,
        transaction: FinancialTransaction,
        data: Dict[str, Any],
        updated_by
    ) -> ServiceResult:
        """
        Met à jour une transaction existante.
        
        Args:
            transaction: La transaction à mettre à jour
            data: Dictionnaire contenant les données à mettre à jour
            updated_by: Utilisateur qui effectue la mise à jour
        
        Returns:
            ServiceResult avec data={'transaction': transaction} si succès
        """
        try:
            # Vérifier que la transaction peut être modifiée
            if transaction.status == FinancialTransaction.Status.VALIDE:
                return ServiceResult.fail("Une transaction validée ne peut pas être modifiée.")
            
            # Mettre à jour les champs fournis
            updatable_fields = [
                'transaction_type', 'amount', 'transaction_date',
                'payment_method', 'category', 'description',
                'member', 'event', 'notes'
            ]
            
            for field in updatable_fields:
                if field in data:
                    value = data[field]
                    if field == 'amount':
                        value = Decimal(str(value))
                    setattr(transaction, field, value)
            
            transaction.save()
            
            return ServiceResult.ok({'transaction': transaction})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de la mise à jour de la transaction: {str(e)}")
    
    @classmethod
    def validate_transaction(
        cls,
        transaction: FinancialTransaction,
        validated_by
    ) -> ServiceResult:
        """
        Valide une transaction en attente.
        
        Args:
            transaction: La transaction à valider
            validated_by: Utilisateur qui valide la transaction
        
        Returns:
            ServiceResult avec data={'transaction': transaction} si succès
        """
        try:
            if transaction.status != FinancialTransaction.Status.EN_ATTENTE:
                return ServiceResult.fail("Seules les transactions en attente peuvent être validées.")
            
            transaction.status = FinancialTransaction.Status.VALIDE
            transaction.validated_by = validated_by
            transaction.validated_at = timezone.now()
            transaction.save()
            
            return ServiceResult.ok({'transaction': transaction})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de la validation de la transaction: {str(e)}")
    
    @classmethod
    def cancel_transaction(
        cls,
        transaction: FinancialTransaction,
        cancelled_by,
        reason: str = ''
    ) -> ServiceResult:
        """
        Annule une transaction.
        
        Args:
            transaction: La transaction à annuler
            cancelled_by: Utilisateur qui annule la transaction
            reason: Raison de l'annulation (optionnel)
        
        Returns:
            ServiceResult avec data={'transaction': transaction} si succès
        """
        try:
            if transaction.status == FinancialTransaction.Status.ANNULE:
                return ServiceResult.fail("Cette transaction est déjà annulée.")
            
            transaction.status = FinancialTransaction.Status.ANNULE
            if reason:
                transaction.notes = f"{transaction.notes}\n[Annulé par {cancelled_by}]: {reason}".strip()
            transaction.save()
            
            return ServiceResult.ok({'transaction': transaction})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de l'annulation de la transaction: {str(e)}")
    
    @classmethod
    def get_dashboard_stats(cls, site=None) -> Dict[str, Any]:
        """
        Retourne les statistiques pour le dashboard financier.
        
        Args:
            site: Site pour filtrer les statistiques (optionnel)
        
        Returns:
            Dictionnaire contenant les statistiques
        """
        today = date.today()
        start_of_month = today.replace(day=1)
        start_of_year = today.replace(month=1, day=1)
        
        # Filtre de base
        base_filter = Q(status=FinancialTransaction.Status.VALIDE)
        if site:
            base_filter &= Q(site=site)
        
        # Stats du mois
        month_filter = base_filter & Q(transaction_date__gte=start_of_month)
        month_transactions = FinancialTransaction.objects.filter(month_filter)
        
        month_income = month_transactions.filter(
            transaction_type__in=['don', 'dime', 'offrande']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        month_expenses = month_transactions.filter(
            transaction_type='depense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Stats de l'année
        year_filter = base_filter & Q(transaction_date__gte=start_of_year)
        year_transactions = FinancialTransaction.objects.filter(year_filter)
        
        year_income = year_transactions.filter(
            transaction_type__in=['don', 'dime', 'offrande']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        year_expenses = year_transactions.filter(
            transaction_type='depense'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Transactions en attente
        pending_filter = Q(status=FinancialTransaction.Status.EN_ATTENTE)
        if site:
            pending_filter &= Q(site=site)
        pending_count = FinancialTransaction.objects.filter(pending_filter).count()
        
        # Transactions récentes
        recent_filter = base_filter if site else Q()
        recent_transactions = FinancialTransaction.objects.filter(
            recent_filter
        ).select_related('category', 'member').order_by(
            '-transaction_date', '-created_at'
        )[:10]
        
        return {
            'month_income': month_income,
            'month_expenses': month_expenses,
            'month_balance': month_income - month_expenses,
            'year_income': year_income,
            'year_expenses': year_expenses,
            'year_balance': year_income - year_expenses,
            'pending_count': pending_count,
            'recent_transactions': recent_transactions,
        }
    
    @classmethod
    def get_monthly_donations_data(cls, months: int = 12, site=None) -> Dict[str, Any]:
        """
        Retourne les données de dons par mois pour les graphiques.
        
        Args:
            months: Nombre de mois à récupérer (défaut: 12)
            site: Site pour filtrer (optionnel)
        
        Returns:
            Dictionnaire avec labels (mois) et data (montants)
        """
        from datetime import datetime
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth
        
        # Calculer la date de début
        today = date.today()
        start_date = today.replace(day=1)
        for _ in range(months - 1):
            if start_date.month == 1:
                start_date = start_date.replace(year=start_date.year - 1, month=12)
            else:
                start_date = start_date.replace(month=start_date.month - 1)
        
        # Filtre de base
        base_filter = Q(
            status=FinancialTransaction.Status.VALIDE,
            transaction_type__in=['don', 'dime', 'offrande'],
            transaction_date__gte=start_date
        )
        if site:
            base_filter &= Q(site=site)
        
        # Grouper par mois et sommer les montants
        monthly_data = FinancialTransaction.objects.filter(
            base_filter
        ).annotate(
            month=TruncMonth('transaction_date')
        ).values('month').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        # Créer les labels et données pour tous les mois (même ceux sans données)
        labels = []
        data = []
        current_date = start_date
        
        # Convertir les résultats en dictionnaire pour un accès rapide
        monthly_totals = {
            item['month'].date().replace(day=1): float(item['total'] or 0)
            for item in monthly_data
        }
        
        for _ in range(months):
            # Format du label (ex: "Jan 2024")
            labels.append(current_date.strftime('%b %Y'))
            
            # Montant pour ce mois (0 si pas de données)
            month_key = current_date
            data.append(monthly_totals.get(month_key, 0))
            
            # Passer au mois suivant
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)
        
        return {
            'labels': labels,
            'data': data,
            'total': sum(data),
            'average': sum(data) / len(data) if data else 0
        }
    
    @classmethod
    def get_expenses_distribution_data(cls, months: int = 12, site=None) -> Dict[str, Any]:
        """
        Retourne les données de répartition des dépenses par catégorie pour les graphiques.
        
        Args:
            months: Nombre de mois à analyser (défaut: 12)
            site: Site pour filtrer (optionnel)
        
        Returns:
            Dictionnaire avec labels (catégories) et data (montants)
        """
        from django.db.models import Sum
        
        # Calculer la date de début
        today = date.today()
        start_date = today.replace(day=1)
        for _ in range(months - 1):
            if start_date.month == 1:
                start_date = start_date.replace(year=start_date.year - 1, month=12)
            else:
                start_date = start_date.replace(month=start_date.month - 1)
        
        # Filtre de base pour les dépenses
        base_filter = Q(
            status=FinancialTransaction.Status.VALIDE,
            transaction_type='depense',
            transaction_date__gte=start_date
        )
        if site:
            base_filter &= Q(site=site)
        
        # Grouper par catégorie et sommer les montants
        category_data = FinancialTransaction.objects.filter(
            base_filter
        ).values(
            'category__name'
        ).annotate(
            total=Sum('amount')
        ).order_by('-total')
        
        # Préparer les données pour le graphique
        labels = []
        data = []
        colors = [
            '#EF4444',  # Rouge
            '#F59E0B',  # Orange
            '#10B981',  # Vert
            '#3B82F6',  # Bleu
            '#8B5CF6',  # Violet
            '#EC4899',  # Rose
            '#06B6D4',  # Cyan
            '#84CC16',  # Lime
            '#F97316',  # Orange foncé
            '#6366F1',  # Indigo
        ]
        
        total_expenses = Decimal('0')
        
        for i, item in enumerate(category_data):
            category_name = item['category__name'] or 'Sans catégorie'
            amount = float(item['total'] or 0)
            
            labels.append(category_name)
            data.append(amount)
            total_expenses += Decimal(str(amount))
        
        # Si pas de données, retourner des données vides
        if not data:
            return {
                'labels': ['Aucune dépense'],
                'data': [0],
                'colors': ['#E5E7EB'],
                'total': 0,
                'count': 0
            }
        
        # Limiter à 10 catégories max, regrouper le reste dans "Autres"
        if len(data) > 10:
            other_amount = sum(data[10:])
            labels = labels[:10] + ['Autres']
            data = data[:10] + [other_amount]
        
        # Assigner les couleurs
        chart_colors = colors[:len(data)]
        
        return {
            'labels': labels,
            'data': data,
            'colors': chart_colors,
            'total': float(total_expenses),
            'count': len(labels)
        }
    
    @classmethod
    def get_transactions_by_period(
        cls,
        start_date: date,
        end_date: date,
        transaction_type: str = None,
        status: str = None,
        site=None
    ) -> List[FinancialTransaction]:
        """
        Récupère les transactions pour une période donnée.
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            transaction_type: Type de transaction (optionnel)
            status: Statut (optionnel)
            site: Site (optionnel)
        
        Returns:
            Liste des transactions
        """
        filters = Q(transaction_date__gte=start_date, transaction_date__lte=end_date)
        
        if transaction_type:
            filters &= Q(transaction_type=transaction_type)
        if status:
            filters &= Q(status=status)
        if site:
            filters &= Q(site=site)
        
        return FinancialTransaction.objects.filter(filters).select_related(
            'category', 'member', 'recorded_by'
        ).order_by('-transaction_date')
    
    @classmethod
    def calculate_totals(
        cls,
        transactions: List[FinancialTransaction]
    ) -> Dict[str, Decimal]:
        """
        Calcule les totaux pour une liste de transactions.
        
        Args:
            transactions: Liste des transactions
        
        Returns:
            Dictionnaire avec total_income, total_expenses, balance
        """
        total_income = Decimal('0')
        total_expenses = Decimal('0')
        
        for transaction in transactions:
            if transaction.is_income:
                total_income += transaction.amount
            else:
                total_expenses += transaction.amount
        
        return {
            'total_income': total_income,
            'total_expenses': total_expenses,
            'balance': total_income - total_expenses
        }


class BudgetService:
    """
    Service de gestion des budgets.
    
    Centralise la logique métier pour les opérations sur les budgets,
    les lignes de budget et les demandes de budget.
    """
    
    @classmethod
    def create_budget(
        cls,
        name: str,
        year: int,
        created_by,
        group=None,
        department=None,
        description: str = ''
    ) -> ServiceResult:
        """
        Crée un nouveau budget.
        
        Args:
            name: Nom du budget
            year: Année du budget
            created_by: Utilisateur qui crée le budget
            group: Groupe associé (optionnel)
            department: Département associé (optionnel)
            description: Description (optionnel)
        
        Returns:
            ServiceResult avec data={'budget': budget} si succès
        """
        try:
            # Vérifier qu'au moins un groupe ou département est spécifié
            if not group and not department:
                return ServiceResult.fail("Un groupe ou un département doit être spécifié.")
            
            # Vérifier qu'un budget n'existe pas déjà pour cette entité et cette année
            existing_filter = Q(year=year)
            if group:
                existing_filter &= Q(group=group)
            if department:
                existing_filter &= Q(department=department)
            
            if Budget.objects.filter(existing_filter).exists():
                entity_name = group.name if group else department.name
                return ServiceResult.fail(
                    f"Un budget existe déjà pour {entity_name} en {year}."
                )
            
            budget = Budget.objects.create(
                name=name,
                year=year,
                group=group,
                department=department,
                description=description,
                created_by=created_by,
                total_requested=Decimal('0.00'),
                status=Budget.Status.DRAFT
            )
            
            return ServiceResult.ok({'budget': budget})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de la création du budget: {str(e)}")
    
    @classmethod
    def add_budget_item(
        cls,
        budget: Budget,
        category: BudgetCategory,
        requested_amount: Decimal,
        description: str,
        justification: str = '',
        priority: int = 3
    ) -> ServiceResult:
        """
        Ajoute une ligne au budget.
        
        Args:
            budget: Le budget auquel ajouter la ligne
            category: Catégorie de la ligne
            requested_amount: Montant demandé
            description: Description de la ligne
            justification: Justification (optionnel)
            priority: Priorité 1-5 (défaut: 3)
        
        Returns:
            ServiceResult avec data={'item': item} si succès
        """
        try:
            if budget.status != Budget.Status.DRAFT:
                return ServiceResult.fail(
                    "Les lignes ne peuvent être ajoutées qu'aux budgets en brouillon."
                )
            
            # Vérifier si une ligne existe déjà pour cette catégorie
            if BudgetItem.objects.filter(budget=budget, category=category).exists():
                return ServiceResult.fail(
                    f"Une ligne existe déjà pour la catégorie {category.name}."
                )
            
            item = BudgetItem.objects.create(
                budget=budget,
                category=category,
                requested_amount=requested_amount,
                description=description,
                justification=justification,
                priority=priority
            )
            
            # Mettre à jour le total du budget
            cls._update_budget_total(budget)
            
            return ServiceResult.ok({'item': item})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de l'ajout de la ligne: {str(e)}")
    
    @classmethod
    def update_budget_item(
        cls,
        item: BudgetItem,
        data: Dict[str, Any]
    ) -> ServiceResult:
        """
        Met à jour une ligne de budget.
        
        Args:
            item: La ligne à mettre à jour
            data: Dictionnaire contenant les données à mettre à jour
        
        Returns:
            ServiceResult avec data={'item': item} si succès
        """
        try:
            if item.budget.status != Budget.Status.DRAFT:
                return ServiceResult.fail(
                    "Les lignes ne peuvent être modifiées que dans les budgets en brouillon."
                )
            
            updatable_fields = ['requested_amount', 'description', 'justification', 'priority']
            
            for field in updatable_fields:
                if field in data:
                    value = data[field]
                    if field == 'requested_amount':
                        value = Decimal(str(value))
                    setattr(item, field, value)
            
            item.save()
            
            # Mettre à jour le total du budget
            cls._update_budget_total(item.budget)
            
            return ServiceResult.ok({'item': item})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de la mise à jour de la ligne: {str(e)}")
    
    @classmethod
    def submit_budget(cls, budget: Budget) -> ServiceResult:
        """
        Soumet un budget pour approbation.
        
        Args:
            budget: Le budget à soumettre
        
        Returns:
            ServiceResult avec data={'budget': budget} si succès
        """
        try:
            if budget.status != Budget.Status.DRAFT:
                return ServiceResult.fail("Seuls les budgets en brouillon peuvent être soumis.")
            
            if not budget.items.exists():
                return ServiceResult.fail("Le budget doit contenir au moins une ligne.")
            
            budget.status = Budget.Status.SUBMITTED
            budget.submitted_at = timezone.now()
            budget.save()
            
            return ServiceResult.ok({'budget': budget})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de la soumission du budget: {str(e)}")
    
    @classmethod
    def approve_budget_item(
        cls,
        item: BudgetItem,
        approved_amount: Decimal,
        approved_by,
        comments: str = ''
    ) -> ServiceResult:
        """
        Approuve une ligne de budget.
        
        Args:
            item: La ligne à approuver
            approved_amount: Montant approuvé
            approved_by: Utilisateur qui approuve
            comments: Commentaires (optionnel)
        
        Returns:
            ServiceResult avec data={'item': item} si succès
        """
        try:
            if item.budget.status not in [Budget.Status.SUBMITTED, Budget.Status.APPROVED]:
                return ServiceResult.fail(
                    "Les lignes ne peuvent être approuvées que dans les budgets soumis."
                )
            
            item.approved_amount = approved_amount
            item.approval_status = (
                BudgetItem.ApprovalStatus.APPROVED if approved_amount > 0 
                else BudgetItem.ApprovalStatus.REJECTED
            )
            item.approved_by = approved_by
            item.approved_at = timezone.now()
            item.approval_comments = comments
            item.save()
            
            return ServiceResult.ok({'item': item})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de l'approbation de la ligne: {str(e)}")
    
    @classmethod
    def reject_budget_item(
        cls,
        item: BudgetItem,
        rejected_by,
        reason: str
    ) -> ServiceResult:
        """
        Rejette une ligne de budget.
        
        Args:
            item: La ligne à rejeter
            rejected_by: Utilisateur qui rejette
            reason: Raison du rejet
        
        Returns:
            ServiceResult avec data={'item': item} si succès
        """
        try:
            if item.budget.status not in [Budget.Status.SUBMITTED, Budget.Status.APPROVED]:
                return ServiceResult.fail(
                    "Les lignes ne peuvent être rejetées que dans les budgets soumis."
                )
            
            item.approved_amount = Decimal('0')
            item.approval_status = BudgetItem.ApprovalStatus.REJECTED
            item.approved_by = rejected_by
            item.approved_at = timezone.now()
            item.rejection_reason = reason
            item.save()
            
            return ServiceResult.ok({'item': item})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors du rejet de la ligne: {str(e)}")
    
    @classmethod
    def finalize_budget_approval(
        cls,
        budget: Budget,
        approved_by,
        notes: str = ''
    ) -> ServiceResult:
        """
        Finalise l'approbation d'un budget.
        
        Args:
            budget: Le budget à finaliser
            approved_by: Utilisateur qui approuve
            notes: Notes d'approbation (optionnel)
        
        Returns:
            ServiceResult avec data={'budget': budget} si succès
        """
        try:
            if budget.status != Budget.Status.SUBMITTED:
                return ServiceResult.fail(
                    "Seuls les budgets soumis peuvent être finalisés."
                )
            
            # Calculer le total approuvé
            total_approved = sum(
                item.approved_amount for item in budget.items.all()
            )
            
            budget.total_approved = total_approved
            budget.status = Budget.Status.APPROVED
            budget.approved_by = approved_by
            budget.approved_at = timezone.now()
            budget.approval_notes = notes
            budget.save()
            
            return ServiceResult.ok({'budget': budget})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de la finalisation du budget: {str(e)}")
    
    @classmethod
    def activate_budget(cls, budget: Budget) -> ServiceResult:
        """
        Active un budget approuvé.
        
        Args:
            budget: Le budget à activer
        
        Returns:
            ServiceResult avec data={'budget': budget} si succès
        """
        try:
            if budget.status != Budget.Status.APPROVED:
                return ServiceResult.fail(
                    "Seuls les budgets approuvés peuvent être activés."
                )
            
            budget.status = Budget.Status.ACTIVE
            budget.save()
            
            return ServiceResult.ok({'budget': budget})
            
        except Exception as e:
            return ServiceResult.fail(f"Erreur lors de l'activation du budget: {str(e)}")
    
    @classmethod
    def get_budget_stats(cls, year: int = None) -> Dict[str, Any]:
        """
        Retourne les statistiques des budgets.
        
        Args:
            year: Année pour filtrer (optionnel, défaut: année courante)
        
        Returns:
            Dictionnaire contenant les statistiques
        """
        if year is None:
            year = date.today().year
        
        active_budgets = Budget.objects.filter(
            year=year,
            status=Budget.Status.ACTIVE
        )
        
        total_approved = active_budgets.aggregate(
            total=Sum('total_approved')
        )['total'] or Decimal('0.00')
        
        total_spent = sum(budget.spent_amount for budget in active_budgets)
        
        pending_requests = BudgetRequest.objects.filter(
            status=BudgetRequest.Status.PENDING
        ).count()
        
        # Stats par statut
        budget_stats = {}
        for status_code, status_name in Budget.Status.choices:
            count = Budget.objects.filter(year=year, status=status_code).count()
            budget_stats[status_name] = count
        
        return {
            'year': year,
            'total_approved': total_approved,
            'total_spent': total_spent,
            'remaining_budget': total_approved - total_spent,
            'utilization_percentage': (
                float(total_spent / total_approved * 100) 
                if total_approved > 0 else 0
            ),
            'pending_requests': pending_requests,
            'budget_stats': budget_stats,
            'active_budgets_count': active_budgets.count(),
        }
    
    @classmethod
    def get_low_budget_items(cls, threshold_percent: float = 80.0) -> List[BudgetItem]:
        """
        Récupère les lignes de budget avec un taux d'utilisation élevé.
        
        Args:
            threshold_percent: Seuil de pourcentage (défaut: 80%)
        
        Returns:
            Liste des lignes de budget dépassant le seuil
        """
        year = date.today().year
        active_budgets = Budget.objects.filter(
            year=year,
            status=Budget.Status.ACTIVE
        )
        
        low_budget_items = []
        for budget in active_budgets:
            for item in budget.items.all():
                if item.approved_amount > 0:
                    utilization = item.utilization_percentage
                    if utilization >= threshold_percent:
                        low_budget_items.append(item)
        
        return low_budget_items
    
    @classmethod
    def _update_budget_total(cls, budget: Budget):
        """
        Met à jour le total demandé du budget.
        
        Args:
            budget: Le budget à mettre à jour
        """
        total = sum(item.requested_amount for item in budget.items.all())
        budget.total_requested = total
        budget.save(update_fields=['total_requested'])
