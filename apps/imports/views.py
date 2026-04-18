from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q
import io
import logging
import pandas as pd

from .models import ImportLog
from .forms import ImportForm
from .services import ExcelImportService, generate_template_excel, export_members_to_excel, export_children_to_excel, export_young_members_to_excel
from apps.core.permissions import role_required

logger = logging.getLogger(__name__)

ALLOWED_IMPORT_EXTENSIONS = {'.xlsx', '.xls'}
MAX_IMPORT_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@login_required
@role_required('admin', 'secretariat')
def import_list(request):
    """
    Liste des imports effectués.
    """
    imports = ImportLog.objects.all()
    
    # Filtres
    import_type = request.GET.get('type')
    status = request.GET.get('status')
    search = request.GET.get('search')
    
    if import_type:
        imports = imports.filter(import_type=import_type)
    
    if status:
        imports = imports.filter(status=status)
    
    if search:
        imports = imports.filter(
            Q(file_name__icontains=search) |
            Q(imported_by__username__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(imports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'import_types': ImportLog.ImportType.choices,
        'statuses': ImportLog.Status.choices,
        'current_type': import_type,
        'current_status': status,
        'search': search or '',
    }
    
    return render(request, 'imports/import_list.html', context)


@login_required
@role_required('admin', 'secretariat')
def import_create(request):
    """
    Créer un nouvel import.
    """
    if request.method == 'POST':
        form = ImportForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES.get('file')
            if uploaded_file:
                import os
                ext = os.path.splitext(uploaded_file.name)[1].lower()
                if ext not in ALLOWED_IMPORT_EXTENSIONS:
                    messages.error(request, 'Type de fichier non autorisé. Seuls les fichiers Excel (.xlsx, .xls) sont acceptés.')
                    return render(request, 'imports/import_create.html', {'form': form, 'import_types': ImportLog.ImportType.choices})
                if uploaded_file.size > MAX_IMPORT_FILE_SIZE:
                    messages.error(request, 'Fichier trop volumineux. La taille maximale est de 10 Mo.')
                    return render(request, 'imports/import_create.html', {'form': form, 'import_types': ImportLog.ImportType.choices})

            import_log = form.save(commit=False)
            import_log.imported_by = request.user
            import_log.save()
            
            # Traitement synchrone de l'import
            try:
                service = ExcelImportService(import_log)
                service.process_import()
                messages.success(request, 'Import terminé avec succès.')
            except Exception as e:
                logger.error(f"Erreur lors de l'import {import_log.pk}: {e}")
                import_log.status = ImportLog.Status.FAILED
                import_log.error_message = str(e)
                import_log.save(update_fields=['status', 'error_message'])
                messages.warning(request, "L'import a rencontré une erreur. Consultez les détails.")
            
            return redirect('imports:detail', pk=import_log.pk)
    else:
        form = ImportForm()
    
    context = {
        'form': form,
        'import_types': ImportLog.ImportType.choices,
    }
    
    return render(request, 'imports/import_create.html', context)


@login_required
@role_required('admin', 'secretariat')
def import_detail(request, pk):
    """
    Détail d'un import.
    """
    import_log = get_object_or_404(ImportLog, pk=pk)
    
    context = {
        'import_log': import_log,
    }
    
    return render(request, 'imports/import_detail.html', context)


@login_required
@role_required('admin', 'secretariat')
def import_status(request, pk):
    """
    API pour récupérer le statut d'un import (AJAX).
    """
    import_log = get_object_or_404(ImportLog, pk=pk)
    
    data = {
        'status': import_log.status,
        'status_display': import_log.get_status_display(),
        'total_rows': import_log.total_rows,
        'processed_rows': import_log.processed_rows,
        'success_rows': import_log.success_rows,
        'error_rows': import_log.error_rows,
        'success_rate': import_log.success_rate,
        'completed': import_log.status in [ImportLog.Status.SUCCESS, ImportLog.Status.ERROR, ImportLog.Status.PARTIAL],
        'duration': str(import_log.duration) if import_log.duration else None,
    }
    
    return JsonResponse(data)


@login_required
def download_template(request, import_type):
    """
    Télécharger un template Excel pour l'import.
    """
    if import_type not in ['members', 'children', 'young_members']:
        messages.error(request, 'Type d\'import invalide.')
        return redirect('imports:list')
    
    try:
        df = generate_template_excel(import_type)
        
        # Créer le fichier Excel en mémoire
        output = io.BytesIO()
        
        # Utiliser pandas pour créer le fichier Excel
        import pandas as pd
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Données')
            
            # Ajouter une feuille d'instructions
            instructions_data = {
                'Colonne': list(df.columns),
                'Description': _get_column_descriptions(import_type),
                'Obligatoire': _get_required_columns(import_type),
                'Format': _get_column_formats(import_type)
            }
            
            instructions_df = pd.DataFrame(instructions_data)
            instructions_df.to_excel(writer, index=False, sheet_name='Instructions')
        
        output.seek(0)
        
        # Préparer la réponse
        filename = f'template_import_{import_type}_{timezone.now().strftime("%Y%m%d")}.xlsx'
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        messages.error(request, f'Erreur lors de la génération du template: {str(e)}')
        return redirect('imports:list')


def _get_column_descriptions(import_type):
    """Retourne les descriptions des colonnes selon le type d'import."""
    if import_type == 'members':
        return [
            'Prénom du membre', 'Nom de famille', 'Adresse email', 'Numéro de téléphone',
            'Date de naissance (JJ/MM/AAAA)', 'Genre (M ou F)', 'Adresse complète',
            'Ville de résidence', 'Code postal', 'Profession', 'Statut (actif/inactif/visiteur)',
            'Date d\'arrivée à l\'église', 'Baptisé (oui/non)', 'Date de baptême',
            'Situation familiale', 'Notes diverses'
        ]
    elif import_type == 'children':
        return [
            'Prénom de l\'enfant', 'Nom de famille', 'Date de naissance (JJ/MM/AAAA)',
            'Genre (M ou F)', 'Nom complet du père', 'Téléphone du père', 'Email du père',
            'Nom complet de la mère', 'Téléphone de la mère', 'Email de la mère',
            'Nom du contact d\'urgence', 'Téléphone d\'urgence', 'Allergies connues',
            'Notes médicales', 'Besoin de transport (oui/non)', 'Adresse de ramassage',
            'Notes diverses'
        ]
    elif import_type == 'young_members':
        return [
            'Prénom du jeune', 'Nom de famille', 'Date de naissance (JJ/MM/AAAA)',
            'Genre (M ou F)', 'Numéro de téléphone', 'Adresse email',
            'Adresse complète', 'Ville', 'Code postal',
            'Nom du parent / responsable', 'Téléphone parent', 'Email parent',
            'Nom du contact d\'urgence', 'Téléphone d\'urgence',
            'Allergies connues', 'Notes médicales',
            'Baptisé (oui/non)', 'Date de baptême',
            'Né de nouveau (oui/non)', 'Date de conversion',
            'Besoin de transport (oui/non)', 'Adresse de ramassage',
            'Statut (actif/inactif/visiteur)', 'Notes diverses'
        ]


def _get_required_columns(import_type):
    """Retourne si les colonnes sont obligatoires."""
    if import_type == 'members':
        required = ['Oui', 'Oui', 'Non', 'Non', 'Non', 'Non', 'Non', 'Non', 'Non', 'Non',
                   'Non', 'Non', 'Non', 'Non', 'Non', 'Non']
    elif import_type == 'children':
        required = ['Oui', 'Oui', 'Oui', 'Oui', 'Oui', 'Oui', 'Non', 'Non', 'Non', 'Non',
                   'Non', 'Non', 'Non', 'Non', 'Non', 'Non', 'Non']
    elif import_type == 'young_members':
        required = ['Oui', 'Oui', 'Oui', 'Non', 'Non', 'Non',
                   'Non', 'Non', 'Non',
                   'Non', 'Non', 'Non',
                   'Non', 'Non',
                   'Non', 'Non',
                   'Non', 'Non',
                   'Non', 'Non',
                   'Non', 'Non',
                   'Non', 'Non']
    
    return required


def _get_column_formats(import_type):
    """Retourne les formats attendus pour les colonnes."""
    if import_type == 'members':
        return [
            'Texte', 'Texte', 'Email', 'Téléphone', 'JJ/MM/AAAA', 'M ou F', 'Texte',
            'Texte', 'Texte', 'Texte', 'actif/inactif/visiteur', 'JJ/MM/AAAA',
            'oui/non', 'JJ/MM/AAAA', 'Texte', 'Texte'
        ]
    elif import_type == 'children':
        return [
            'Texte', 'Texte', 'JJ/MM/AAAA', 'M ou F', 'Texte', 'Téléphone', 'Email',
            'Texte', 'Téléphone', 'Email', 'Texte', 'Téléphone', 'Texte', 'Texte',
            'oui/non', 'Texte', 'Texte'
        ]
    elif import_type == 'young_members':
        return [
            'Texte', 'Texte', 'JJ/MM/AAAA', 'M ou F', 'Téléphone', 'Email',
            'Texte', 'Texte', 'Texte',
            'Texte', 'Téléphone', 'Email',
            'Texte', 'Téléphone',
            'Texte', 'Texte',
            'oui/non', 'JJ/MM/AAAA',
            'oui/non', 'JJ/MM/AAAA',
            'oui/non', 'Texte',
            'actif/inactif/visiteur', 'Texte'
        ]


@login_required
def export_members(request):
    """
    Exporte tous les membres actifs vers un fichier Excel.
    """
    try:
        # Générer le DataFrame avec les données des membres
        df = export_members_to_excel()
        
        # Créer le fichier Excel en mémoire
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Membres')
            
            # Ajouter des informations sur l'export
            info_data = {
                'Information': ['Date d\'export', 'Nombre de membres', 'Utilisateur'],
                'Valeur': [
                    timezone.now().strftime('%d/%m/%Y %H:%M'),
                    len(df),
                    request.user.get_full_name() or request.user.username
                ]
            }
            
            info_df = pd.DataFrame(info_data)
            info_df.to_excel(writer, index=False, sheet_name='Informations')
        
        output.seek(0)
        
        # Préparer la réponse
        filename = f'export_membres_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        messages.success(request, f'{len(df)} membres exportés avec succès!')
        return response
        
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'export des membres: {str(e)}')
        return redirect('members:list')


@login_required
def export_children(request):
    """
    Exporte tous les enfants actifs vers un fichier Excel.
    """
    try:
        # Générer le DataFrame avec les données des enfants
        df = export_children_to_excel()
        
        # Créer le fichier Excel en mémoire
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Enfants')
            
            # Ajouter des informations sur l'export
            info_data = {
                'Information': ['Date d\'export', 'Nombre d\'enfants', 'Utilisateur'],
                'Valeur': [
                    timezone.now().strftime('%d/%m/%Y %H:%M'),
                    len(df),
                    request.user.get_full_name() or request.user.username
                ]
            }
            
            info_df = pd.DataFrame(info_data)
            info_df.to_excel(writer, index=False, sheet_name='Informations')
        
        output.seek(0)
        
        # Préparer la réponse
        filename = f'export_enfants_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        messages.success(request, f'{len(df)} enfants exportés avec succès!')
        return response
        
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'export des enfants: {str(e)}')
        return redirect('bibleclub:children_list')


@login_required
def export_young_members(request):
    """
    Exporte tous les jeunes actifs vers un fichier Excel.
    """
    try:
        df = export_young_members_to_excel()
        
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Jeunes')
            
            info_data = {
                'Information': ['Date d\'export', 'Nombre de jeunes', 'Utilisateur'],
                'Valeur': [
                    timezone.now().strftime('%d/%m/%Y %H:%M'),
                    len(df),
                    request.user.get_full_name() or request.user.username
                ]
            }
            
            info_df = pd.DataFrame(info_data)
            info_df.to_excel(writer, index=False, sheet_name='Informations')
        
        output.seek(0)
        
        filename = f'export_jeunes_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        messages.success(request, f'{len(df)} jeunes exportés avec succès!')
        return response
        
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'export des jeunes: {str(e)}')
        return redirect('young:member_list')


@login_required
def export_hub(request):
    """
    Hub central de tous les exports et imports disponibles.
    """
    try:
        from .export_config import ExportConfig, get_user_exports, get_export_stats
        from .services import ExportHistoryService
        
        # Exports disponibles pour l'utilisateur
        user_exports = get_user_exports(request.user)
        
        # Statistiques des exports
        export_stats = get_export_stats()

        can_access_finance_import = (
            request.user.is_superuser or
            request.user.is_admin or
            request.user.has_any_role('admin', 'finance')
        )

        if can_access_finance_import:
            finance_import_config = ExportConfig(
                name='Import Finance Excel',
                description='Importer categories, budgets, previsionnels et transactions depuis un classeur Excel avec modele et simulation.',
                icon='bi-file-earmark-arrow-up',
                url_name='finance:import_excel',
                category='Finances',
                format_type='import',
                sensitive=True,
            )
            user_exports.setdefault('Finances', []).append(('finance_import_excel', finance_import_config))
            export_stats['total'] += 1
            export_stats['sensitive_count'] += 1
            export_stats['by_format']['import'] = export_stats['by_format'].get('import', 0) + 1
            export_stats['by_category']['Finances'] = export_stats['by_category'].get('Finances', 0) + 1
        
        # Historique récent des exports
        recent_exports = ExportHistoryService.get_export_history(
            user=request.user if not request.user.is_superuser else None,
            limit=5
        )
        
        context = {
            'user_exports': user_exports,
            'export_stats': export_stats,
            'recent_exports': recent_exports,
            'is_admin': request.user.is_superuser,
        }
        
        return render(request, 'imports/export_hub.html', context)
        
    except Exception as e:
        # En cas d'erreur, rediriger vers la liste des imports
        messages.error(request, f'Erreur lors du chargement du hub: {str(e)}')
        return redirect('imports:list')


@login_required
def export_groups(request):
    """Exporte les groupes de l'église."""
    from .services import GenericExportService, ExportHistoryService
    
    try:
        df = GenericExportService.export_groups()
        
        info_data = {
            'Information': ['Date d\'export', 'Nombre de groupes', 'Utilisateur'],
            'Valeur': [
                timezone.now().strftime('%d/%m/%Y %H:%M'),
                len(df),
                request.user.get_full_name() or request.user.username
            ]
        }
        
        filename = f'export_groupes_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        # Log de l'export
        ExportHistoryService.log_export(
            user=request.user,
            export_type='groups',
            export_name='Groupes',
            record_count=len(df)
        )
        
        response = GenericExportService.create_excel_response(
            data=df,
            filename=filename,
            sheet_name='Groupes',
            info_data=info_data
        )
        
        messages.success(request, f'{len(df)} groupes exportés avec succès!')
        return response
        
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'export des groupes: {str(e)}')
        return redirect('imports:hub')


@login_required
def export_inventory(request):
    """Exporte l'inventaire des équipements."""
    from .services import GenericExportService, ExportHistoryService
    
    try:
        df = GenericExportService.export_inventory()
        
        info_data = {
            'Information': ['Date d\'export', 'Nombre d\'équipements', 'Utilisateur'],
            'Valeur': [
                timezone.now().strftime('%d/%m/%Y %H:%M'),
                len(df),
                request.user.get_full_name() or request.user.username
            ]
        }
        
        filename = f'export_inventaire_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        # Log de l'export
        ExportHistoryService.log_export(
            user=request.user,
            export_type='inventory',
            export_name='Inventaire',
            record_count=len(df)
        )
        
        response = GenericExportService.create_excel_response(
            data=df,
            filename=filename,
            sheet_name='Inventaire',
            info_data=info_data
        )
        
        messages.success(request, f'{len(df)} équipements exportés avec succès!')
        return response
        
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'export de l\'inventaire: {str(e)}')
        return redirect('imports:hub')


@login_required
def export_transport(request):
    """Exporte les données de transport."""
    from .services import GenericExportService, ExportHistoryService
    
    try:
        df = GenericExportService.export_transport()
        
        info_data = {
            'Information': ['Date d\'export', 'Nombre de chauffeurs', 'Utilisateur'],
            'Valeur': [
                timezone.now().strftime('%d/%m/%Y %H:%M'),
                len(df),
                request.user.get_full_name() or request.user.username
            ]
        }
        
        filename = f'export_transport_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        # Log de l'export
        ExportHistoryService.log_export(
            user=request.user,
            export_type='transport',
            export_name='Transport',
            record_count=len(df)
        )
        
        response = GenericExportService.create_excel_response(
            data=df,
            filename=filename,
            sheet_name='Chauffeurs',
            info_data=info_data
        )
        
        messages.success(request, f'{len(df)} chauffeurs exportés avec succès!')
        return response
        
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'export du transport: {str(e)}')
        return redirect('imports:hub')


@login_required
def export_communication(request):
    """Exporte les logs de communication."""
    from .services import GenericExportService, ExportHistoryService
    
    try:
        df = GenericExportService.export_communication_logs()
        
        info_data = {
            'Information': ['Date d\'export', 'Nombre de logs', 'Utilisateur', 'Période'],
            'Valeur': [
                timezone.now().strftime('%d/%m/%Y %H:%M'),
                len(df),
                request.user.get_full_name() or request.user.username,
                '3 derniers mois'
            ]
        }
        
        filename = f'export_communication_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx'
        
        # Log de l'export
        ExportHistoryService.log_export(
            user=request.user,
            export_type='communication',
            export_name='Logs Communication',
            record_count=len(df)
        )
        
        response = GenericExportService.create_excel_response(
            data=df,
            filename=filename,
            sheet_name='Logs Communication',
            info_data=info_data
        )
        
        messages.success(request, f'{len(df)} logs exportés avec succès!')
        return response
        
    except Exception as e:
        messages.error(request, f'Erreur lors de l\'export des logs: {str(e)}')
        return redirect('imports:export_hub')


@login_required
def import_delete(request, pk):
    """Supprimer un log d'import et le fichier associé."""
    import_log = get_object_or_404(ImportLog, pk=pk)
    
    if request.method == 'POST':
        # Supprimer le fichier physique si existant
        if import_log.file_path:
            import_log.file_path.delete(save=False)
            
        import_log.delete()
        messages.success(request, 'Journal d\'import supprimé avec succès.')
        return redirect('imports:list')
    
    return render(request, 'imports/import_confirm_delete.html', {'import_log': import_log})


@login_required
def import_bulk_delete(request):
    """Suppression de plusieurs logs d'import en une seule opération."""
    if request.method == 'POST':
        ids = request.POST.getlist('selected_ids')
        if not ids:
            messages.warning(request, 'Aucun import sélectionné.')
            return redirect('imports:list')
        
        logs = ImportLog.objects.filter(pk__in=ids)
        count = logs.count()
        
        # Supprimer les fichiers physiques
        for log in logs:
            if log.file_path:
                try:
                    log.file_path.delete(save=False)
                except Exception:
                    pass
        
        logs.delete()
        messages.success(request, f'{count} journal(aux) d\'import supprimé(s) avec succès.')
    
    return redirect('imports:list')