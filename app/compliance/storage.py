import os
import uuid
from typing import Tuple
from cryptography.fernet import Fernet
from config.settings import settings


def _get_fernet() -> Tuple[Fernet, str]:
    """Return a Fernet instance and key id."""
    key = settings.DOCUMENT_ENCRYPTION_KEY
    if not key:
        key = Fernet.generate_key().decode()
        settings.DOCUMENT_ENCRYPTION_KEY = key
    return Fernet(key.encode()), key


def save_encrypted_data(data: bytes, directory: str) -> Tuple[str, str]:
    os.makedirs(directory, exist_ok=True)
    f, key_id = _get_fernet()
    ciphertext = f.encrypt(data)
    file_id = str(uuid.uuid4())
    path = os.path.join(directory, file_id)
    with open(path, "wb") as out:
        out.write(ciphertext)
    return path, key_id


def decrypt_file(path: str, key_id: str) -> bytes:
    f = Fernet(key_id.encode())
    with open(path, "rb") as infile:
        data = infile.read()
    return f.decrypt(data)
