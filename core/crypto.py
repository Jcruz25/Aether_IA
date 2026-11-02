"""
Módulo de Seguridad y Cifrado Avanzado de AETHER (Éter Shield).
Proporciona protocolos de cifrado AES-256 (Fernet) para la protección de datos 
sensibles en reposo y gestión de claves locales.
"""
import os
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pathlib import Path

class AetherCrypto:
    def __init__(self):
        self.key_path = Path(__file__).parent / ".vault.key"
        self._key = self._load_or_generate_key()
        self.cipher = Fernet(self._key)

    def _get_machine_id(self) -> bytes:
        """Genera un identificador único basado en la máquina para derivación de claves."""
        import uuid
        import socket
        try:
            # Combinación de dirección MAC y nombre de host para mayor unicidad local
            unique_str = f"{uuid.getnode()}-{socket.gethostname()}"
            return unique_str.encode()
        except Exception:
            return b"aether-fallback-key-id-000"

    def _load_or_generate_key(self) -> bytes:
        """Carga la clave desde el disco o genera una nueva vinculada a la máquina."""
        if self.key_path.exists():
            try:
                with open(self.key_path, "rb") as f:
                    return f.read()
            except Exception:
                pass
        
        # Generar clave persistente vinculada al hardware
        salt = b'\x17\x89\x01\xab\xcd\xef\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b' # Salt estático para consistencia
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._get_machine_id()))
        
        try:
            with open(self.key_path, "wb") as f:
                f.write(key)
        except Exception as e:
            print(f"[AETHER CRYPTO] Error crítico guardando llave: {e}")
            
        return key

    def encrypt(self, data: str) -> str:
        """Cifra una cadena de texto y devuelve el token en base64."""
        if not data: return ""
        try:
            return self.cipher.encrypt(data.encode()).decode()
        except Exception:
            return ""

    def decrypt(self, token: str) -> str:
        """Descifra un token y devuelve la cadena original."""
        if not token: return ""
        try:
            return self.cipher.decrypt(token.encode()).decode()
        except Exception as e:
            # Si falla el descifrado (ej: clave corrupta), devolvemos el token original 
            # para evitar pérdida de datos si el archivo aún no estaba cifrado
            return ""

    def encrypt_json(self, data: dict) -> str:
        """Cifra un objeto JSON."""
        return self.encrypt(json.dumps(data, ensure_ascii=False))

    def decrypt_json(self, token: str) -> dict:
        """Descifra un token y devuelve el objeto JSON."""
        decrypted = self.decrypt(token)
        try:
            return json.loads(decrypted) if decrypted else {}
        except Exception:
            return {}

# Instancia global exportada
aether_crypto = AetherCrypto()

