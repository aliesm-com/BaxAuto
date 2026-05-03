from django.db import models

from .encryption import decrypt_connection_secret, encrypt_connection_secret


class EncryptedTextField(models.TextField):
    """Stores ciphertext in the DB; exposes decrypted str to Python code."""

    description = 'Encrypted text (Fernet)'

    def get_internal_type(self):
        return 'TextField'

    def from_db_value(self, value, expression, connection):
        if value is None:
            return ''
        return decrypt_connection_secret(value)

    def to_python(self, value):
        if value is None:
            return ''
        return str(value)

    def get_prep_value(self, value):
        if value is None or value == '':
            return ''
        return encrypt_connection_secret(value)
