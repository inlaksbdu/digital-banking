from cryptography.fernet import Fernet
from django.conf import settings
import base64


class PinEncryption:
    def __init__(self):
        key = settings.SECRET_KEY.encode()
        padded_key = base64.urlsafe_b64encode(key.ljust(32)[:32])
        self._fernet = Fernet(padded_key)

    def encrypt_pin(self, secret: str) -> str:
        return self._fernet.encrypt(secret.encode()).decode()

    def decrypt_pin(self, encrypted_str: str) -> str:
        decrypted = self._fernet.decrypt(encrypted_str.encode()).decode()
        return str(decrypted)
