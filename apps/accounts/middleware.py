"""
Middleware pour forcer le changement de mot de passe.
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout


class ForcePasswordChangeMiddleware:
    """
    Middleware qui force les utilisateurs à changer leur mot de passe
    s'ils ont le flag must_change_password activé.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifier si l'utilisateur est connecté et doit changer son mot de passe
        if (request.user.is_authenticated and 
            hasattr(request.user, 'must_change_password') and 
            request.user.must_change_password):
            
            # URLs autorisées même si l'utilisateur doit changer son mot de passe
            allowed_paths = [
                reverse('accounts:first_login_password_change'),
                reverse('accounts:logout'),
                '/admin/logout/',
            ]
            
            # URLs qui ne nécessitent pas de vérification
            exempt_paths = [
                reverse('accounts:login'),
                reverse('public:home'),
                '/admin/login/',
            ]
            
            current_path = request.path
            
            # Permettre les URLs autorisées
            if current_path in allowed_paths:
                response = self.get_response(request)
                return response
            
            # Permettre les URLs exemptées (mais déconnecter l'utilisateur)
            if current_path in exempt_paths:
                from django.contrib.auth import logout
                logout(request)
                response = self.get_response(request)
                return response
            
            # Permettre les ressources statiques et media
            if (current_path.startswith('/static/') or 
                current_path.startswith('/media/') or
                current_path.startswith('/favicon.ico')):
                response = self.get_response(request)
                return response
            
            # Rediriger vers le changement de mot de passe pour toute autre URL
            # Générer un token pour le changement de mot de passe
            from .services import AuthenticationService
            from django.http import HttpResponseRedirect
            
            token = AuthenticationService.generate_password_change_token(request.user)
            url = reverse('accounts:first_login_password_change')
            return HttpResponseRedirect(f'{url}?token={token}')
        
        response = self.get_response(request)
        return response