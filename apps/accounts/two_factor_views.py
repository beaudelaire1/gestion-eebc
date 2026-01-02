"""
Vues pour la Double Authentification (2FA).
"""

from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.http import JsonResponse


class TwoFactorSetupView(LoginRequiredMixin, TemplateView):
    """Configuration de la 2FA."""
    template_name = 'accounts/two_factor_setup.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Si pas encore de secret, en générer un
        if not user.two_factor_secret:
            backup_codes = user.setup_two_factor()
            context['backup_codes'] = backup_codes
            context['show_backup_codes'] = True
        
        context['qr_code'] = user.get_totp_qr_code()
        context['secret'] = user.two_factor_secret
        context['is_enabled'] = user.two_factor_enabled
        
        return context
    
    def post(self, request):
        """Confirme la configuration 2FA."""
        user = request.user
        code = request.POST.get('code', '').strip()
        
        if not code:
            messages.error(request, "Veuillez entrer le code de vérification.")
            return redirect('accounts:two_factor_setup')
        
        if user.confirm_two_factor(code):
            messages.success(request, "Double authentification activée avec succès !")
            return redirect('accounts:profile')
        else:
            messages.error(request, "Code invalide. Veuillez réessayer.")
            return redirect('accounts:two_factor_setup')


class TwoFactorDisableView(LoginRequiredMixin, View):
    """Désactivation de la 2FA."""
    
    def post(self, request):
        user = request.user
        code = request.POST.get('code', '').strip()
        
        # Vérifier le code avant de désactiver
        if user.verify_two_factor_code(code):
            user.disable_two_factor()
            messages.success(request, "Double authentification désactivée.")
        else:
            messages.error(request, "Code invalide.")
        
        return redirect('accounts:profile')


class TwoFactorVerifyView(TemplateView):
    """Vérification du code 2FA lors de la connexion."""
    template_name = 'accounts/two_factor_verify.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Vérifier qu'il y a un utilisateur en attente de 2FA
        if 'two_factor_user_id' not in request.session:
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)
    
    def post(self, request):
        from .models import User
        
        user_id = request.session.get('two_factor_user_id')
        code = request.POST.get('code', '').strip()
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            del request.session['two_factor_user_id']
            return redirect('accounts:login')
        
        if user.verify_two_factor_code(code):
            # Connexion réussie
            del request.session['two_factor_user_id']
            login(request, user)
            
            next_url = request.session.pop('two_factor_next', None)
            return redirect(next_url or 'dashboard:home')
        else:
            messages.error(request, "Code invalide. Veuillez réessayer.")
            return redirect('accounts:two_factor_verify')


class TwoFactorBackupCodesView(LoginRequiredMixin, TemplateView):
    """Affiche et régénère les codes de secours."""
    template_name = 'accounts/two_factor_backup_codes.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_2fa'] = self.request.user.two_factor_enabled
        return context
    
    def post(self, request):
        """Régénère les codes de secours."""
        user = request.user
        code = request.POST.get('code', '').strip()
        
        # Vérifier le code actuel
        if not user.verify_two_factor_code(code):
            messages.error(request, "Code invalide.")
            return redirect('accounts:two_factor_backup_codes')
        
        # Régénérer les codes
        from .two_factor import generate_backup_codes, hash_backup_code
        import json
        
        backup_codes = generate_backup_codes(10)
        hashed_codes = [hash_backup_code(c) for c in backup_codes]
        user.two_factor_backup_codes = json.dumps(hashed_codes)
        user.save()
        
        return render(request, self.template_name, {
            'backup_codes': backup_codes,
            'show_new_codes': True,
            'has_2fa': True,
        })
