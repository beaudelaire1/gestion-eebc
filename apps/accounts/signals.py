"""Account security signals.

Changes to authorization or MFA state invalidate all refresh tokens so a
previously issued mobile session cannot outlive a privilege/security change.
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from apps.core.security import revoke_user_refresh_tokens
from .models import User


SECURITY_FIELDS = {
    'password',
    'role',
    'is_active',
    'is_staff',
    'is_superuser',
    'two_factor_enabled',
    'two_factor_secret',
}


@receiver(pre_save, sender=User)
def remember_security_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._security_state_changed = False
        return
    previous = sender.objects.filter(pk=instance.pk).values(*SECURITY_FIELDS).first()
    if not previous:
        instance._security_state_changed = False
        return
    instance._security_state_changed = any(
        previous[field] != getattr(instance, field) for field in SECURITY_FIELDS
    )


@receiver(post_save, sender=User)
def revoke_tokens_after_security_change(sender, instance, created, **kwargs):
    if not created and getattr(instance, '_security_state_changed', False):
        revoke_user_refresh_tokens(instance)
