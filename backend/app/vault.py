import base64
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import settings

logger = logging.getLogger("stokvigil.vault")

class CryptoVault:
    def __init__(self, raw_secret_key: str = None):
        # Production Environment Key Audit - Strict Fatal Enforcement
        if settings.ENVIRONMENT == "production":
            if not settings.ENCRYPTION_KEY or settings.ENCRYPTION_KEY.startswith("d3d3d3"):
                logger.critical("FATAL: Missing or placeholder ENCRYPTION_KEY in production environment.")
                raise RuntimeError(
                    "FATAL SECURITY CONFIGURATION: Dedicated ENCRYPTION_KEY environment variable is required in production mode."
                )
        else:
            key_source = raw_secret_key or settings.ENCRYPTION_KEY
            if not key_source:
                if settings.ENVIRONMENT == "test":
                    key_source = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
                else:
                    logger.warning("No ENCRYPTION_KEY configured in development. Generating ephemeral vault key.")
                    key_source = Fernet.generate_key().decode()

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
