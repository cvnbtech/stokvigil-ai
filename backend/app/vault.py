import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import settings

logger = logging.getLogger("stokvigil.vault")

class CryptoVault:
    def __init__(self, raw_secret_key: str = None):
        key_source = raw_secret_key or settings.ENCRYPTION_KEY
        
        # Production Environment Key Audit - Strict Enforcement
        if settings.ENVIRONMENT == "production":
            if not key_source or key_source.startswith("d3d3d3"):
                raise RuntimeError(
                    "CRITICAL SECURITY ERROR: Default/weak ENCRYPTION_KEY detected in production mode. "
                    "You must set a unique, strong ENCRYPTION_KEY environment variable in your deployment settings."
                )

        # Ensure valid 32-byte urlsafe base64 key for Fernet
        if len(key_source) != 44 or not key_source.endswith('='):
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'stokvigil_vault_salt_2026',
                iterations=100000,
            )
            derived_key = kdf.derive(key_source.encode())
            self.key = base64.urlsafe_b64encode(derived_key)
        else:
            self.key = key_source.encode()
            
        self.fernet = Fernet(self.key)

    def encrypt(self, plain_text: str) -> str:
        """Encrypts plaintext string to Fernet AES-256 ciphertext."""
        if not plain_text:
            return ""
        encrypted_bytes = self.fernet.encrypt(plain_text.encode('utf-8'))
        return encrypted_bytes.decode('utf-8')

    def decrypt(self, cipher_text: str) -> str:
        """Decrypts Fernet AES-256 ciphertext back to plaintext string."""
        if not cipher_text:
            return ""
        decrypted_bytes = self.fernet.decrypt(cipher_text.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')

# Singleton vault instance
vault = CryptoVault()
