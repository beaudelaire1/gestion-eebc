"""MFA gate for authentication flows that previously logged users in directly."""

from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse

from . import views as legacy_views


def first_login_password_change_with_mfa(request):
    """Keep MFA mandatory after the required first/password-reset change flow."""
    response = legacy_views.first_login_password_change(request)

    if (
        request.method == 'POST'
        and request.user.is_authenticated
        and request.user.two_factor_enabled
    ):
        user_id = request.user.pk

        # The legacy password-change view has just authenticated the user.
        # Destroy that authenticated session before creating the pending MFA
        # challenge so the password change cannot become an MFA bypass.
        logout(request)
        request.session['two_factor_user_id'] = user_id
        request.session['two_factor_next'] = reverse('dashboard:home')
        request.session['two_factor_attempts'] = 0
        return redirect('accounts:two_factor_verify')

    return response
