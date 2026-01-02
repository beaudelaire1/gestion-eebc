"""
Module de Double Authentification (2FA) pour EEBC.

Implémente :
- TOTP (Time-based One-Time Password) via Google Authenticator, Authy, etc.
- Codes de secours pour récupération
- QR Code pour configuration facile
"""

import pyotp
import qrcode
import io
import base64
import secrets
from django.conf import settings


def generate_totp_secret():
    """Génère une clé secrète TOTP."""
    return pyotp.random_base32()


def get_totp_uri(user, secret):
    """Génère l'URI pour le QR code."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=user.email or user.username,
        issuer_name="EEBC Gestion"
    )


def generate_qr_code(uri):
    """Génère un QR code en base64 pour affichage HTML."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/png;base64,{img_base64}"


def verify_totp(secret, code):
    """Vérifie un code TOTP."""
    if not secret or not code:
        return False
    
    totp = pyotp.TOTP(secret)
    # Accepte le code actuel et les 2 précédents/suivants (fenêtre de 60s)
    return totp.verify(code, valid_window=1)


def generate_backup_codes(count=10):
    """Génère des codes de secours."""
    codes = []
    for _ in range(count):
        # Format: XXXX-XXXX (8 caractères)
        code = f"{secrets.token_hex(2).upper()}-{secrets.token_hex(2).upper()}"
        codes.append(code)
    return codes


def hash_backup_code(code):
    """Hash un code de secours pour stockage sécurisé."""
    import hashlib
    return hashlib.sha256(code.encode()).hexdigest()
