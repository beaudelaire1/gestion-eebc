"""Security-enforcing wrappers for account endpoints.

The legacy views remain focused on rendering/business logic. These wrappers
make privilege boundaries explicit at the routing boundary so every crafted
POST is checked server-side.
"""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from apps.core.security import (
    can_assign_role,
    can_manage_account,
    safe_next_url,
    user_has_any_role,
)
from apps.core.utils.recaptcha import validate_recaptcha
from apps.core.utils.turnstile import validate_turnstile_with_ip

from . import views as legacy_views
from .services import AuthenticationService

User = get_user_model()


def _posted_roles(request, field='roles'):
    values = request.POST.getlist(field)
    roles = []
    for value in values:
        roles.extend(part.strip() for part in str(value).split(',') if part.strip())
    return roles


def _forbid(message):
    return HttpResponseForbidden(message)


def secure_login_view(request):
    """Password login which cannot bypass mandatory password change or MFA."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        captcha_valid = False
        captcha_error = None
        turnstile_site_key = getattr(settings, 'TURNSTILE_SITE_KEY', '')
        if turnstile_site_key:
            captcha_valid, captcha_error = validate_turnstile_with_ip(request)
        elif getattr(settings, 'RECAPTCHA_PUBLIC_KEY', ''):
            captcha_valid, captcha_error = validate_recaptcha(request.POST.get('recaptcha_token'))
        elif settings.DEBUG:
            captcha_valid = True
        else:
            captcha_error = 'Configuration de sécurité manquante.'

        if not captcha_valid:
            messages.error(request, captcha_error or 'Échec de validation de sécurité.')
            return render(request, 'accounts/login.html', {
                'recaptcha_site_key': getattr(settings, 'RECAPTCHA_PUBLIC_KEY', ''),
                'turnstile_site_key': turnstile_site_key,
            })

        if username and password:
            user, error_message = AuthenticationService.authenticate_user(
                username=username,
                password=password,
                request=request,
            )
            if user is not None:
                if user.must_change_password:
                    token = AuthenticationService.generate_password_change_token(user)
                    return redirect(f"{reverse('accounts:first_login_password_change')}?token={token}")

                requested_next = request.GET.get('next') or request.POST.get('next')
                next_url = safe_next_url(
                    request,
                    requested_next,
                    reverse('dashboard:home'),
                )

                if user.two_factor_enabled:
                    # Password is only factor one. No authenticated session exists yet.
                    request.session.cycle_key()
                    request.session['two_factor_user_id'] = user.pk
                    request.session['two_factor_next'] = next_url
                    request.session['two_factor_attempts'] = 0
                    return redirect('accounts:two_factor_verify')

                login(request, user)
                return redirect(next_url)

            messages.error(request, error_message)

    return render(request, 'accounts/login.html', {
        'recaptcha_site_key': getattr(settings, 'RECAPTCHA_PUBLIC_KEY', ''),
        'turnstile_site_key': getattr(settings, 'TURNSTILE_SITE_KEY', ''),
    })


class SecureTwoFactorVerifyView(View):
    template_name = 'accounts/two_factor_verify.html'
    max_attempts = 8

    def dispatch(self, request, *args, **kwargs):
        if 'two_factor_user_id' not in request.session:
            return redirect('accounts:login')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        user_id = request.session.get('two_factor_user_id')
        code = request.POST.get('code', '').strip()
        attempts = int(request.session.get('two_factor_attempts', 0))
        if attempts >= self.max_attempts:
            for key in ('two_factor_user_id', 'two_factor_next', 'two_factor_attempts'):
                request.session.pop(key, None)
            messages.error(request, 'Trop de tentatives de double authentification. Reconnectez-vous.')
            return redirect('accounts:login')

        try:
            user = User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            request.session.flush()
            return redirect('accounts:login')

        if not user.two_factor_enabled:
            # Security state changed while challenge was pending: restart authentication.
            for key in ('two_factor_user_id', 'two_factor_next', 'two_factor_attempts'):
                request.session.pop(key, None)
            return redirect('accounts:login')

        if not user.verify_two_factor_code(code):
            request.session['two_factor_attempts'] = attempts + 1
            messages.error(request, 'Code invalide. Veuillez réessayer.')
            return redirect('accounts:two_factor_verify')

        next_url = safe_next_url(
            request,
            request.session.pop('two_factor_next', None),
            reverse('dashboard:home'),
        )
        request.session.pop('two_factor_user_id', None)
        request.session.pop('two_factor_attempts', None)
        backend = settings.AUTHENTICATION_BACKENDS[0] if getattr(settings, 'AUTHENTICATION_BACKENDS', None) else 'django.contrib.auth.backends.ModelBackend'
        login(request, user, backend=backend)
        return redirect(next_url)


@login_required
def secure_create_user_view(request):
    if request.method == 'POST':
        roles = _posted_roles(request)
        if any(not can_assign_role(request.user, role) for role in roles):
            return _forbid("Seul un administrateur peut attribuer le rôle administrateur.")
    return legacy_views.create_user_view(request)


@login_required
def secure_user_bulk_import_view(request):
    # A spreadsheet can carry a per-row role column. Restrict this high-impact
    # operation to administrators instead of trying to sanitize an opaque file.
    if not user_has_any_role(request.user, 'admin'):
        return _forbid("L'import de comptes est réservé aux administrateurs.")
    return legacy_views.user_bulk_import_view(request)


@login_required
def secure_user_update_view(request, user_id):
    target = User.objects.filter(pk=user_id).first()
    if not can_manage_account(request.user, target):
        return _forbid("Un compte non administrateur ne peut pas modifier un administrateur.")
    if request.method == 'POST':
        roles = _posted_roles(request)
        if any(not can_assign_role(request.user, role) for role in roles):
            return _forbid("Seul un administrateur peut attribuer le rôle administrateur.")
    return legacy_views.user_update_view(request, user_id)


@login_required
def secure_user_delete_view(request, user_id):
    target = User.objects.filter(pk=user_id).first()
    if not can_manage_account(request.user, target):
        return _forbid("Seul un administrateur peut désactiver ou supprimer un administrateur.")
    return legacy_views.user_delete_view(request, user_id)


@login_required
def secure_user_activate_view(request, user_id):
    target = User.objects.filter(pk=user_id).first()
    if not can_manage_account(request.user, target):
        return _forbid("Seul un administrateur peut réactiver un administrateur.")
    return legacy_views.user_activate_view(request, user_id)


@login_required
def secure_reset_user_password(request, user_id):
    target = User.objects.filter(pk=user_id).first()
    if not can_manage_account(request.user, target):
        return _forbid("Seul un administrateur peut réinitialiser le mot de passe d'un administrateur.")
    return legacy_views.reset_user_password(request, user_id)


@login_required
def secure_resend_invitation(request, user_id):
    target = User.objects.filter(pk=user_id).first()
    if not can_manage_account(request.user, target):
        return _forbid("Seul un administrateur peut agir sur un compte administrateur.")
    return legacy_views.resend_invitation(request, user_id)
