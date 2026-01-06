"""
Vues personnalisées pour la gestion des erreurs HTTP.
"""
import logging
from django.shortcuts import render
from django.http import HttpResponseNotFound, HttpResponseServerError, HttpResponseForbidden

logger = logging.getLogger('django.request')


def handler403(request, exception=None):
    """
    Vue personnalisée pour les erreurs 403 (Accès refusé).
    
    Args:
        request: La requête HTTP
        exception: L'exception qui a causé l'erreur (optionnel)
    
    Returns:
        HttpResponseForbidden avec le template 403.html
    """
    # Logger l'accès refusé avec contexte
    logger.warning(
        'Access denied (403) for user %s on path %s',
        getattr(request, 'user', 'Anonymous'),
        request.path,
        extra={
            'request': request,
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'user_role': getattr(request.user, 'role', None) if hasattr(request, 'user') and hasattr(request.user, 'role') else None,
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
    )
    
    context = {
        'request_path': request.path,
        'user': getattr(request, 'user', None),
    }
    
    return HttpResponseForbidden(
        render(request, 'errors/403.html', context).content
    )


def handler404(request, exception=None):
    """
    Vue personnalisée pour les erreurs 404 (Page non trouvée).
    
    Args:
        request: La requête HTTP
        exception: L'exception qui a causé l'erreur (optionnel)
    
    Returns:
        HttpResponseNotFound avec le template 404.html
    """
    # Logger la page non trouvée
    logger.info(
        'Page not found (404) for path %s',
        request.path,
        extra={
            'request': request,
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'ip_address': request.META.get('REMOTE_ADDR'),
            'referer': request.META.get('HTTP_REFERER', ''),
        }
    )
    
    context = {
        'request_path': request.path,
        'user': getattr(request, 'user', None),
    }
    
    return HttpResponseNotFound(
        render(request, 'errors/404.html', context).content
    )


def handler500(request):
    """
    Vue personnalisée pour les erreurs 500 (Erreur interne du serveur).
    
    Args:
        request: La requête HTTP
    
    Returns:
        HttpResponseServerError avec le template 500.html
    """
    import traceback
    import sys
    from datetime import datetime
    
    # Capturer les informations de l'exception actuelle
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    # Préparer le contexte complet pour le logging
    error_context = {
        'request': request,
        'timestamp': datetime.now().isoformat(),
        'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') and request.user.is_authenticated else None,
        'username': getattr(request.user, 'username', 'Anonymous') if hasattr(request, 'user') else 'Anonymous',
        'user_role': getattr(request.user, 'role', None) if hasattr(request, 'user') and hasattr(request.user, 'role') else None,
        'ip_address': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        'referer': request.META.get('HTTP_REFERER', ''),
        'method': request.method,
        'path': request.path,
        'full_path': request.get_full_path(),
        'get_params': dict(request.GET),
        'post_params': dict(request.POST) if request.method == 'POST' else {},
        'session_key': request.session.session_key if hasattr(request, 'session') else None,
        'is_ajax': request.headers.get('X-Requested-With') == 'XMLHttpRequest',
        'is_htmx': request.headers.get('HX-Request') == 'true',
        'content_type': request.content_type,
        'encoding': getattr(request, 'encoding', None),
    }
    
    # Ajouter les informations de l'exception si disponibles
    if exc_type and exc_value:
        error_context.update({
            'exception_type': exc_type.__name__,
            'exception_message': str(exc_value),
            'exception_traceback': traceback.format_exception(exc_type, exc_value, exc_traceback),
        })
    
    # Logger l'erreur serveur avec contexte complet
    logger.error(
        'Internal Server Error (500) for path %s - User: %s (%s) - Exception: %s: %s',
        request.path,
        error_context['username'],
        error_context['user_id'],
        error_context.get('exception_type', 'Unknown'),
        error_context.get('exception_message', 'No exception info'),
        exc_info=True,
        extra=error_context
    )
    
    # Logger également dans l'audit log si possible
    try:
        from apps.core.models import AuditLog
        AuditLog.objects.create(
            user=request.user if hasattr(request, 'user') and request.user.is_authenticated else None,
            action=AuditLog.Action.SERVER_ERROR if hasattr(AuditLog.Action, 'SERVER_ERROR') else 'server_error',
            model_name='System',
            object_repr=f"500 Error on {request.path}",
            changes={
                'error_type': error_context.get('exception_type', 'Unknown'),
                'error_message': error_context.get('exception_message', 'No details'),
                'path': request.path,
                'method': request.method,
            },
            ip_address=error_context['ip_address'],
            user_agent=error_context['user_agent'][:500] if error_context['user_agent'] else '',
        )
    except Exception as audit_error:
        # Si l'audit log échoue aussi, logger cette erreur séparément
        logger.critical(
            'Failed to create audit log for 500 error: %s',
            str(audit_error),
            exc_info=True
        )
    
    # Pour les erreurs 500, on ne peut pas garantir que le contexte Django fonctionne
    # donc on utilise un template minimal
    try:
        context = {
            'request_path': request.path,
            'error_id': f"ERR-500-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        }
        return HttpResponseServerError(
            render(request, 'errors/500.html', context).content
        )
    except Exception as e:
        # Si même le rendu du template échoue, retourner une réponse HTML basique
        logger.critical(
            'Failed to render 500 error template: %s',
            str(e),
            exc_info=True,
            extra=error_context
        )
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Erreur serveur - Gestion EEBC</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .error {{ color: #d32f2f; }}
                .error-id {{ font-family: monospace; background: #f5f5f5; padding: 5px; }}
            </style>
        </head>
        <body>
            <h1 class="error">Erreur interne du serveur</h1>
            <p>Une erreur inattendue s'est produite. Veuillez réessayer plus tard.</p>
            <p class="error-id">Code d'erreur: ERR-500-{datetime.now().strftime('%Y%m%d%H%M%S')}</p>
            <p>Contactez le support à <a href="mailto:support@eebc.org">support@eebc.org</a></p>
        </body>
        </html>
        """
        
        return HttpResponseServerError(html_content)