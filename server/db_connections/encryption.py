"""Fernet encrypt/decrypt for reversible secrets (e.g. DB connection passwords)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    key = (getattr(settings, 'DB_CREDENTIALS_FERNET_KEY', None) or '').strip()
    if key:
        return Fernet(key.encode('ascii'))
    digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_connection_secret(plaintext: str) -> str:
    if plaintext is None or plaintext == '':
        return ''
    return _fernet().encrypt(plaintext.encode('utf-8')).decode('ascii')


def decrypt_connection_secret(ciphertext: str) -> str:
    if ciphertext is None or ciphertext == '':
        return ''
    try:
        return _fernet().decrypt(ciphertext.encode('ascii')).decode('utf-8')
    except InvalidToken:
        # Plain-text rows saved before encryption was enabled.
        return ciphertext
