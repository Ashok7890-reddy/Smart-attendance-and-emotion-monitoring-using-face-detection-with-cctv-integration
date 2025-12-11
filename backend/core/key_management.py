"""
Secure key management system for the Smart Attendance System.
"""

import os
import json
import base64
import secrets
import logging
from typing import Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class KeyMetadata:
    """Metadata for encryption keys."""
    key_id: str
    purpose: str
    algorithm: str
    created_at: str
    expires_at: Optional[str] = None
    rotation_count: int = 0
    is_active: bool = True


class SecureKeyManager:
    """Manages encryption keys securely with rotation and versioning."""
    
    def __init__(self, key_store_path: str = "keys"):
        """Initialize key manager."""
        self.key_store_path = Path(key_store_path)
        self.key_store_path.mkdir(mode=0o700, exist_ok=True)
        
        # Key files
        self.master_key_file = self.key_store_path / "master.key"
        self.keys_metadata_file = self.key_store_path / "keys_metadata