from django.db import migrations


def encrypt_existing_secrets(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    from apps.accounts.two_factor_security import encrypt_totp_secret, is_encrypted_secret

    for user in User.objects.exclude(two_factor_secret='').iterator():
        if not is_encrypted_secret(user.two_factor_secret):
            user.two_factor_secret = encrypt_totp_secret(user.two_factor_secret)
            user.save(update_fields=['two_factor_secret'])


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0008_expand_two_factor_secret'),
    ]

    operations = [
        migrations.RunPython(encrypt_existing_secrets, migrations.RunPython.noop),
    ]
