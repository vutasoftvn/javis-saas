import os
import sys
import uuid
import base64
import hashlib
from typing import Optional

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None
    print("[secrets] missing cryptography lib - secrets won't be properly encrypted", file=sys.stderr)

MASTER_SECRET_KEY = os.environ.get("MASTER_SECRET_KEY", "default-insecure-master-key-for-dev")

def _derive_workspace_key(workspace_id: uuid.UUID) -> bytes:
    # Derive a 32-byte url-safe base64 key from master key + workspace_id
    combined = f"{MASTER_SECRET_KEY}:{workspace_id}".encode("utf-8")
    digest = hashlib.sha256(combined).digest()
    return base64.urlsafe_b64encode(digest)

def _get_fernet(workspace_id: uuid.UUID) -> Optional['Fernet']:
    if Fernet is None:
        return None
    key = _derive_workspace_key(workspace_id)
    return Fernet(key)

def encrypt_for_workspace(workspace_id: uuid.UUID, value: str) -> str:
    if not isinstance(value, str) or not value or value.startswith(("enc:", "plain:")):
        return value
    f = _get_fernet(workspace_id)
    if not f:
        return "plain:" + value
    return "enc:" + f.encrypt(value.encode("utf-8")).decode("ascii")

def decrypt_for_workspace(workspace_id: uuid.UUID, value: str) -> str:
    if not isinstance(value, str) or not value:
        return value or ""
    if value.startswith("plain:"):
        return value[len("plain:"):]
    if value.startswith("enc:"):
        f = _get_fernet(workspace_id)
        if not f:
            return "" # Cannot decrypt without lib
        try:
            return f.decrypt(value[len("enc:"):].encode("ascii")).decode("utf-8")
        except Exception:
            return ""
    return value
