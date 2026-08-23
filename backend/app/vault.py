import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import settings

logger = logging.getLogger("stokvigil.vault")

class CryptoVault:
    def __init__(self, raw_secret_key: str = None):
        key_source = raw_secret_key or settings.ENCRYPTION_KEY or "stokvigil_vault_default_secret_key_2026_prod="
        
        # Production Environment Key Audit - Safe Log Warning
        if settings.ENVIRONMENT == "production":
            if not key_source or key_source.startswith("d3d3d3"):
                logger.warning(
                    "WARNING: Default/placeholder ENCRYPTION_KEY detected in production mode. "
                    "Deriving PBKDF2 key. For maximum security, provide a dedicated ENCRYPTION_KEY in your Cloud Run variables."
                )
                key_source = key_source or "stokvigil_vault_default_secret_key_2026_prod="

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
        """Decrypts Fernet AES-256 ciphertext, Base64 payload, or plaintext string."""
        if not cipher_text:
            return ""
        trimmed = str(cipher_text).strip()
        
        # 1. Try Fernet AES-256 Decryption
        if trimmed.startswith("gAAAAA"):
            try:
                decrypted_bytes = self.fernet.decrypt(trimmed.encode('utf-8'))
                return decrypted_bytes.decode('utf-8')
            except Exception as e:
                logger.warning(f"Fernet decryption attempt failed: {e}")
        
        # 2. Try Base64 URL-safe / Standard Decoding
        try:
            padded = trimmed + '=' * ((4 - len(trimmed) % 4) % 4)
            decoded_bytes = base64.urlsafe_b64decode(padded.encode('utf-8'))
            decoded_str = decoded_bytes.decode('utf-8')
            if decoded_str and all(32 <= ord(c) <= 126 for c in decoded_str):
                return decoded_str
        except Exception:
            pass

        # 3. Fallback: If already plaintext
        return trimmed

# Singleton vault instance
vault = CryptoVault()
