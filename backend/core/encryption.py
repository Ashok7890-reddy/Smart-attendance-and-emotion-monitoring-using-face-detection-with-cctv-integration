"""
Encryption utilities for face embeddings and sensitive data.
"""

import os
import base64
import hashlib
from typing import Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import numpy as np
import logging

logger = logging.getLogger(__name__)


class EncryptionManager:
    """Manages encryption and decryption of sensitive data."""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encryption manager with key."""
        if encryption_key:
            self._key = encryption_key.encode()
        else:
            self._key = os.getenv("ENCRYPTION_KEY", "").encode()
            
        if not self._key:
            raise ValueError("Encryption key not provided. Set ENCRYPTION_KEY environment variable.")
        
        self._fernet = self._create_fernet_cipher()
    
    def _create_fernet_cipher(self) -> Fernet:
        """Create Fernet cipher from key."""
        # Use PBKDF2 to derive a proper key from the provided key
        salt = b'smart_attendance_salt'  # In production, use a random salt per encryption
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self._key))
        return Fernet(key)
    
    def encrypt_data(self, data: Union[str, bytes]) -> bytes:
        """Encrypt string or bytes data."""
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            encrypted_data = self._fernet.encrypt(data)
            logger.debug("Data encrypted successfully")
            return encrypted_data
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data and return bytes."""
        try:
            decrypted_data = self._fernet.decrypt(encrypted_data)
            logger.debug("Data decrypted successfully")
            return decrypted_data
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def decrypt_to_string(self, encrypted_data: bytes) -> str:
        """Decrypt data and return string."""
        decrypted_bytes = self.decrypt_data(encrypted_data)
        return decrypted_bytes.decode('utf-8')
    
    def encrypt_face_embedding(self, embedding: np.ndarray) -> bytes:
        """Encrypt face embedding numpy array."""
        try:
            # Convert numpy array to bytes
            embedding_bytes = embedding.tobytes()
            
            # Create metadata for reconstruction
            metadata = {
                'shape': embedding.shape,
                'dtype': str(embedding.dtype)
            }
            metadata_str = f"{str(metadata['shape'])}|{metadata['dtype']}"
            
            # Combine metadata and embedding data
            combined_data = metadata_str.encode('utf-8') + b'||' + embedding_bytes
            
            # Encrypt the combined data
            encrypted_embedding = self.encrypt_data(combined_data)
            logger.debug(f"Face embedding encrypted: shape={embedding.shape}, dtype={embedding.dtype}")
            
            return encrypted_embedding
            
        except Exception as e:
            logger.error(f"Face embedding encryption failed: {e}")
            raise
    
    def decrypt_face_embedding(self, encrypted_embedding: bytes) -> np.ndarray:
        """Decrypt face embedding and return numpy array."""
        try:
            # Decrypt the data
            decrypted_data = self.decrypt_data(encrypted_embedding)
            
            # Split metadata and embedding data
            separator_pos = decrypted_data.find(b'||')
            if separator_pos == -1:
                raise ValueError("Invalid encrypted embedding format - no separator found")
            
            metadata_str = decrypted_data[:separator_pos].decode('utf-8')
            embedding_bytes = decrypted_data[separator_pos + 2:]
            
            # Parse metadata - format is "shape|dtype"
            parts = metadata_str.split('|')
            if len(parts) != 2:
                raise ValueError(f"Invalid metadata format - expected 2 parts, got {len(parts)}: {metadata_str}")
            
            shape_str = parts[0]
            dtype_str = parts[1]
            shape = eval(shape_str)  # Safe since we control the format
            dtype = np.dtype(dtype_str)
            
            # Reconstruct numpy array
            embedding = np.frombuffer(embedding_bytes, dtype=dtype).reshape(shape)
            logger.debug(f"Face embedding decrypted: shape={shape}, dtype={dtype}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Face embedding decryption failed: {e}")
            raise
    
    def hash_data(self, data: Union[str, bytes]) -> str:
        """Create SHA-256 hash of data for indexing/comparison."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        hash_obj = hashlib.sha256(data)
        return hash_obj.hexdigest()
    
    def hash_face_embedding(self, embedding: np.ndarray) -> str:
        """Create hash of face embedding for quick comparison."""
        embedding_bytes = embedding.tobytes()
        return self.hash_data(embedding_bytes)


class FaceEmbeddingStorage:
    """Manages storage and retrieval of encrypted face embeddings."""
    
    def __init__(self, encryption_manager: EncryptionManager):
        self.encryption_manager = encryption_manager
    
    def store_embedding(self, student_id: str, embedding: np.ndarray) -> dict:
        """Store face embedding with encryption."""
        try:
            # Encrypt the embedding
            encrypted_embedding = self.encryption_manager.encrypt_face_embedding(embedding)
            
            # Create hash for quick comparison
            embedding_hash = self.encryption_manager.hash_face_embedding(embedding)
            
            # Return storage data
            storage_data = {
                'student_id': student_id,
                'encrypted_embedding': encrypted_embedding,
                'embedding_hash': embedding_hash,
                'embedding_size': len(encrypted_embedding),
                'original_shape': embedding.shape,
                'original_dtype': str(embedding.dtype)
            }
            
            logger.info(f"Face embedding stored for student: {student_id}")
            return storage_data
            
        except Exception as e:
            logger.error(f"Failed to store embedding for student {student_id}: {e}")
            raise
    
    def retrieve_embedding(self, encrypted_embedding: bytes) -> np.ndarray:
        """Retrieve and decrypt face embedding."""
        try:
            embedding = self.encryption_manager.decrypt_face_embedding(encrypted_embedding)
            logger.debug("Face embedding retrieved and decrypted")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to retrieve embedding: {e}")
            raise
    
    def compare_embeddings(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compare two face embeddings using cosine similarity."""
        try:
            # Normalize embeddings
            norm1 = np.linalg.norm(embedding1)
            norm2 = np.linalg.norm(embedding2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # Calculate cosine similarity
            similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
            
            # Convert to similarity score (0-1 range)
            similarity_score = (similarity + 1) / 2
            
            logger.debug(f"Embedding similarity calculated: {similarity_score:.4f}")
            return float(similarity_score)
            
        except Exception as e:
            logger.error(f"Embedding comparison failed: {e}")
            return 0.0
    
    def calculate_distance(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate Euclidean distance between embeddings."""
        try:
            distance = np.linalg.norm(embedding1 - embedding2)
            logger.debug(f"Embedding distance calculated: {distance:.4f}")
            return float(distance)
            
        except Exception as e:
            logger.error(f"Distance calculation failed: {e}")
            return float('inf')


# Global encryption manager instance
_encryption_manager = None
_face_embedding_storage = None


def get_encryption_manager() -> EncryptionManager:
    """Get global encryption manager instance."""
    global _encryption_manager
    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()
    return _encryption_manager


def get_face_embedding_storage() -> FaceEmbeddingStorage:
    """Get global face embedding storage instance."""
    global _face_embedding_storage
    if _face_embedding_storage is None:
        encryption_manager = get_encryption_manager()
        _face_embedding_storage = FaceEmbeddingStorage(encryption_manager)
    return _face_embedding_storage



# Convenience functions for direct encryption/decryption
def encrypt_data(data: Union[str, bytes]) -> bytes:
    """Encrypt data using the global encryption manager."""
    manager = get_encryption_manager()
    return manager.encrypt_data(data)


def decrypt_data(encrypted_data: bytes) -> bytes:
    """Decrypt data using the global encryption manager."""
    manager = get_encryption_manager()
    return manager.decrypt_data(encrypted_data)


def decrypt_to_string(encrypted_data: bytes) -> str:
    """Decrypt data to string using the global encryption manager."""
    manager = get_encryption_manager()
    return manager.decrypt_to_string(encrypted_data)
