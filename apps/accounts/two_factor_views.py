"""Vues de double authentification (TOTP + codes de secours)."""

import json

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from .models import User
from .two_factor_security import requires_two_factor

MAX_2FA_ATTEMPTS = 5
TWO_FACTOR_LOCK_SECONDS = 10 * 60


def _safe_next_url(request, fallback='dashboard:home'):
    next_url = request.session.pop('two_factor_next', None)
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return fallback


class TwoFactorSetupView(LoginRequiredMixin, TemplateView):
    """Enrôlement TOTP. Les comptes sensibles ne peuvent pas contourner cette étape."""

    template_name = 'accounts/two_factor_setup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Générer le secret et les codes une seule fois. Un simple rafraîchissement
        # ne doit jamais invalider le QR code déjà scanné par l'utilisateur.
        if not user.two_factor_enabled and not user.two_factor_secret:
            backup_codes = user.setup_two_factor()
            context['backup_codes'] = backup_codes
            context['show_backup_codes'] = True

        context['qr_code'] = user.get_totp_qr_code()
        context['secret'] = user.get_two_factor_secret()
        context['is_enabled'] = user.two_factor_enabled
        context['is_required'] = requires_two_factor(user)
        return context

    def post(self, request):
        user = request.user
        code = request.POST.get('code', '').strip()

        if not code:
            messages.error(request, "Veuillez entrer le code de vérification.")
            return redirect('accounts:two_factor_setup')

        if user.confirm_two_factor(code):
            request.session['two_factor_verified_user_id'] = user.pk
            request.session.pop('two_factor_user_id', None)
            messages.success(request, "Double authentification activée.")
            return redirect(_safe_next_url(request, 'accounts:profile'))

        messages.error(request, "Code invalide. Veuillez réessayer.")
        return redirect('accounts:two_factor_setup')


class TwoFactorDisableView(LoginRequiredMixin, View):
    """Désactivation uniquement pour les comptes dont la 2FA est facultative."""

    def post(self, request):
        user = request.user
        if requires_two_factor(user):
            messages.error(
                request,
                "La double authentification est obligatoire pour les responsabilités de ce compte.",
            )
            return redirect('accounts:two_factor_setup')

        code = request.POST.get('code', '').strip()
        if user.verify_two_factor_code(code):
            user.disable_two_factor()
            request.session.pop('two_factor_verified_user_id', None)
            messages.success(request, "Double authentification désactivée.")
        else:
            messages.error(request, "Code invalide.")
        return redirect('accounts:profile')


class TwoFactorVerifyView(TemplateView):
    """Challenge TOTP obligatoire avant l'ouverture d'une session sensible."""

    template_name = 'accounts/two_factor_verify.html'

    def dispatch(self, request, *args, **kwargs):
        user_id = request.session.get('two_factor_user_id')
        if not user_id:
            return redirect('accounts:login')
        if request.user.is_authenticated and request.user.pk != user_id:
            logout(request)
            request.session.flush()
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        user_id = request.session.get('two_factor_user_id')
        code = request.POST.get('code', '').strip()

        try:
            user = User.objects.get(id=user_id, is_active=True)
        except User.DoesNotExist:
            request.session.pop('two_factor_user_id', None)
            return redirect('accounts:login')

        lock_key = f'eebc:2fa:lock:{user.pk}'
        attempts_key = f'eebc:2fa:attempts:{user.pk}'
        if cache.get(lock_key):
            messages.error(request, "Trop de codes invalides. Réessayez dans 10 minutes.")
            return redirect('accounts:two_factor_verify')

        if user.verify_two_factor_code(code):
            cache.delete(attempts_key)
            cache.delete(lock_key)
            if not request.user.is_authenticated:
                login(request, user)
            request.session.pop('two_factor_user_id', None)
            request.session['two_factor_verified_user_id'] = user.pk
            return redirect(_safe_next_url(request))

        attempts = int(cache.get(attempts_key, 0)) + 1
        cache.set(attempts_key, attempts, TWO_FACTOR_LOCK_SECONDS)
        if attempts >= MAX_2FA_ATTEMPTS:
            cache.set(lock_key, True, TWO_FACTOR_LOCK_SECONDS)
            if request.user.is_authenticated:
                logout(request)
            request.session.pop('two_factor_user_id', None)
            messages.error(request, "Trop de codes invalides. Reconnectez-vous dans 10 minutes.")
            return redirect('accounts:login')

        remaining = MAX_2FA_ATTEMPTS - attempts
        messages.error(request, f"Code invalide. {remaining} tentative(s) restante(s).")
        return redirect('accounts:two_factor_verify')


class TwoFactorBackupCodesView(LoginRequiredMixin, TemplateView):
    """Régénération des codes de secours après preuve TOTP/code de secours."""

    template_name = 'accounts/two_factor_backup_codes.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.two_factor_enabled:
            return redirect('accounts:two_factor_setup')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['has_2fa'] = self.request.user.two_factor_enabled
        return context

    def post(self, request):
        user = request.user
        code = request.POST.get('code', '').strip()
        if not user.verify_two_factor_code(code):
            messages.error(request, "Code invalide.")
            return redirect('accounts:two_factor_backup_codes')

        from .two_factor import generate_backup_codes, hash_backup_code

        backup_codes = generate_backup_codes(10)
        user.two_factor_backup_codes = json.dumps(
            [hash_backup_code(item) for item in backup_codes]
        )
        user.save(update_fields=['two_factor_backup_codes'])

        return render(
            request,
            self.template_name,
            {
                'backup_codes': backup_codes,
                'show_new_codes': True,
                'has_2fa': True,
            },
        )
