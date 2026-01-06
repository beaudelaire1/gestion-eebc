"""
URLs pour les exports et impressions PDF.
"""

from django.urls import path
from . import export_views

app_name = 'exports'

urlpatterns = [
    # =========================================================================
    # CLUB BIBLIQUE - Enfants
    # =========================================================================
    path('bibleclub/enfants/excel/', 
         export_views.ChildrenExportView.as_view(), 
         name='children_excel'),
    path('bibleclub/enfants/pdf/', 
         export_views.ChildrenPrintView.as_view(), 
         name='children_print'),
    path('bibleclub/presences/excel/', 
         export_views.AttendanceExportView.as_view(), 
         name='attendance_excel'),
    path('bibleclub/presences/pdf/', 
         export_views.AttendancePrintView.as_view(), 
         name='attendance_print'),
    
    # =========================================================================
    # MEMBRES
    # =========================================================================
    path('membres/excel/', 
         export_views.MembersExportView.as_view(), 
         name='members_excel'),
    path('membres/pdf/', 
         export_views.MembersPrintView.as_view(), 
         name='members_print'),
    
    # =========================================================================
    # FINANCE - Budgets & Transactions
    # =========================================================================
    path('finance/budgets/excel/', 
         export_views.BudgetsExportView.as_view(), 
         name='budgets_excel'),
    path('finance/budgets/pdf/', 
         export_views.BudgetsPrintView.as_view(), 
         name='budgets_print'),
    path('finance/budgets/<int:pk>/excel/', 
         export_views.BudgetDetailExportView.as_view(), 
         name='budget_detail_excel'),
    path('finance/transactions/excel/', 
         export_views.TransactionsExportView.as_view(), 
         name='transactions_excel'),
    
    # =========================================================================
    # ÉVÉNEMENTS
    # =========================================================================
    path('evenements/excel/', 
         export_views.EventsExportView.as_view(), 
         name='events_excel'),
    path('evenements/pdf/', 
         export_views.EventsPrintView.as_view(), 
         name='events_print'),
    
    # =========================================================================
    # GROUPES
    # =========================================================================
    path('groupes/excel/', 
         export_views.GroupsExportView.as_view(), 
         name='groups_excel'),
    path('groupes/pdf/', 
         export_views.GroupsPrintView.as_view(), 
         name='groups_print'),
    path('groupes/<int:pk>/membres/excel/', 
         export_views.GroupMembersExportView.as_view(), 
         name='group_members_excel'),
    
    # =========================================================================
    # DÉPARTEMENTS
    # =========================================================================
    path('departements/excel/', 
         export_views.DepartmentsExportView.as_view(), 
         name='departments_excel'),
    path('departements/pdf/', 
         export_views.DepartmentsPrintView.as_view(), 
         name='departments_print'),
    
    # =========================================================================
    # TRANSPORT
    # =========================================================================
    path('transport/chauffeurs/excel/', 
         export_views.DriversExportView.as_view(), 
         name='drivers_excel'),
    path('transport/chauffeurs/pdf/', 
         export_views.DriversPrintView.as_view(), 
         name='drivers_print'),
    
    # =========================================================================
    # INVENTAIRE
    # =========================================================================
    path('inventaire/excel/', 
         export_views.InventoryExportView.as_view(), 
         name='inventory_excel'),
    path('inventaire/pdf/', 
         export_views.InventoryPrintView.as_view(), 
         name='inventory_print'),
    
    # =========================================================================
    # WORSHIP (Cultes)
    # =========================================================================
    path('worship/cultes/excel/', 
         export_views.WorshipServicesExportView.as_view(), 
         name='worship_services_excel'),
    path('worship/cultes/pdf/', 
         export_views.WorshipServicesPrintView.as_view(), 
         name='worship_services_print'),
    
    # =========================================================================
    # UTILISATEURS
    # =========================================================================
    path('utilisateurs/excel/', 
         export_views.UsersExportView.as_view(), 
         name='users_excel'),
    path('utilisateurs/pdf/', 
         export_views.UsersPrintView.as_view(), 
         name='users_print'),
]
