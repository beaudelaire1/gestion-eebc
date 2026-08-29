"""
Custom exception handler for the API.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent error responses.
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': get_error_message(response),
                'details': response.data if isinstance(response.data, dict) else {'detail': response.data}
            }
        }
        response.data = custom_response_data
    
    return response


def get_error_message(response):
    """Get a human-readable error message from the response."""
    status_messages = {
        400: 'Requête invalide',
        401: 'Non authentifié',
        403: 'Accès refusé',
        404: 'Ressource non trouvée',
        405: 'Méthode non autorisée',
        429: 'Trop de requêtes',
        500: 'Erreur serveur',
    }
    return status_messages.get(response.status_code, 'Erreur')
