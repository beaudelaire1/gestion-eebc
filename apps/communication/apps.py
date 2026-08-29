from django.apps import AppConfig


class CommunicationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.communication"
    verbose_name = "Communication"

    def ready(self):
        # Importer les signaux et les tâches de canal pour les enregistrer.
        import apps.communication.channel_tasks  # noqa: F401
        import apps.communication.signals  # noqa: F401

        # Compatibilité : Announcement possède encore le champ legacy
        # notify_by_sms. Le formulaire n'expose plus cette ambiguïté ; une seule
        # intention déclenche désormais les deux canaux selon les préférences du
        # membre.
        from django import forms

        from apps.communication.forms import AnnouncementForm

        notify_field = AnnouncementForm.base_fields.get("notify_by_email")
        legacy_field = AnnouncementForm.base_fields.get("notify_by_sms")
        if notify_field:
            notify_field.label = "Notifier par email + WhatsApp"
            notify_field.help_text = (
                "Envoie les deux canaux aux membres qui les ont autorisés."
            )
        if legacy_field:
            legacy_field.widget = forms.HiddenInput()
            legacy_field.required = False
            legacy_field.initial = False
