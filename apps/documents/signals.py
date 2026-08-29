from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Document
from .security import is_active_browser_document


@receiver(pre_save, sender=Document)
def reject_active_document_files(sender, instance, **kwargs):
    name = instance.file_name or getattr(instance.file, 'name', '') or ''
    if is_active_browser_document(name, instance.file_type or ''):
        raise ValidationError(
            'Les documents actifs de navigateur (SVG/HTML/JavaScript) sont interdits dans la bibliothèque.'
        )
