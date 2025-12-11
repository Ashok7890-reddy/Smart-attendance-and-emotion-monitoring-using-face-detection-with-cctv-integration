"""
Unit tests for encryption utilities.
"""

import pytest
import numpy as np
from cryptography.fernet import InvalidToken

from backend.core.encryption import EncryptionManager, FaceEmbeddingStorage


class TestEncryptionManager:
    """Test EncryptionManager functionality."""
    
    def test_encryption_manager_creation(self, test_encryption_key):
        """Test EncryptionManager creation with key."""
        manager = EncryptionManager(test_encryption_key)
        assert manager is not None
    
    def test_encryption_manager_without_key(self):
        """Test EncryptionManager creation without key raises error."""
        with pytest.raises(ValueError, match="Encryption key not provided"):
            EncryptionManager("")
    
    def test_string_encryption_decryption(self, encryption_manager):
        """Test string encryption and decryption."""
        original_text = "This is a test string for encryption"
        
        # Encrypt
        encrypted_data = encryption_manager.encrypt_data(original_text)
        assert isinstance(encrypted_data, bytes)
        assert encrypted_data != original_text.encode()
        
        # Decrypt
        decrypted_text = encryption_manager.decrypt_to_string(encrypted_data)
        assert decrypted_text == original_text
    
    def test_bytes_encryption_decryption(self, encryption_manager):
        """Test bytes encryption and decryption."""
        original_bytes = b"This is test bytes data"
        
        # Encrypt
        encrypted_data = encryption_manager.encrypt_data(original_bytes)
        assert isinstance(encrypted_data, bytes)
        assert encrypted_data != original_bytes
        
        # Decrypt
        decrypted_bytes = encryption_manager.decrypt_data(encrypted_data)
        assert decrypted_bytes == original_bytes
    
    def test_face_embedding_encryption_decryption(self, encryption_manager, sample_face_embedding):
        """Test face embedding encryption and decryption."""
        # Encrypt
        encrypted_embedding = encryption_manager.encrypt_face_embedding(sample_face_embedding)
        assert isinstance(encrypted_embedding, bytes)
        
        # Decrypt
        decrypted_embedding = encryption_manager.decrypt_face_embedding(encrypted_embedding)
        assert isinstance(decrypted_embedding, np.ndarray)
        assert decrypted_embedding.shape == sample_face_embedding.shape
        assert decrypted_embedding.dtype == sample_face_embedding.dtype
        np.testing.assert_array_equal(decrypted_embedding, sample_face_embedding)
    
    def test_face_embedding_different_shapes(self, encryption_manager):
        """Test face embedding encryption with different shapes."""
        # Test 1D embedding
        embedding_1d = np.random.rand(128).astype(np.float32)
        encrypted_1d = encryption_manager.encrypt_face_embedding(embedding_1d)
        decrypted_1d = encryption_manager.decrypt_face_embedding(encrypted_1d)
        np.testing.assert_array_equal(decrypted_1d, embedding_1d)
        
        # Test 2D embedding
        embedding_2d = np.random.rand(16, 32).astype(np.float32)
        encrypted_2d = encryption_manager.encrypt_face_embedding(embedding_2d)
        decrypted_2d = encryption_manager.decrypt_face_embedding(encrypted_2d)
        np.testing.assert_array_equal(decrypted_2d, embedding_2d)
    
    def test_face_embedding_different_dtypes(self, encryption_manager):
        """Test face embedding encryption with different data types."""
        # Test float64
        embedding_f64 = np.random.rand(256).astype(np.float64)
        encrypted_f64 = encryption_manager.encrypt_face_embedding(embedding_f64)
        decrypted_f64 = encryption_manager.decrypt_face_embedding(encrypted_f64)
        np.testing.assert_array_equal(decrypted_f64, embedding_f64)
        assert decrypted_f64.dtype == np.float64
        
        # Test int32
        embedding_i32 = np.random.randint(0, 100, 128).astype(np.int32)
        encrypted_i32 = encryption_manager.encrypt_face_embedding(embedding_i32)
        decrypted_i32 = encryption_manager.decrypt_face_embedding(encrypted_i32)
        np.testing.assert_array_equal(decrypted_i32, embedding_i32)
        assert decrypted_i32.dtype == np.int32
    
    def test_invalid_decryption(self, encryption_manager):
        """Test decryption with invalid data."""
        invalid_data = b"invalid_encrypted_data"
        
        with pytest.raises(Exception):  # Should raise InvalidToken or similar
            encryption_manager.decrypt_data(invalid_data)
    
    def test_hash_data(self, encryption_manager):
        """Test data hashing functionality."""
        test_string = "test data for hashing"
        test_bytes = b"test bytes for hashing"
        
        # Hash string
        hash1 = encryption_manager.hash_data(test_string)
        hash2 = encryption_manager.hash_data(test_string)
        assert hash1 == hash2  # Same input should produce same hash
        assert len(hash1) == 64  # SHA-256 produces 64-character hex string
        
        # Hash bytes
        hash3 = encryption_manager.hash_data(test_bytes)
        assert len(hash3) == 64
        
        # Different inputs should produce different hashes
        hash4 = encryption_manager.hash_data("different data")
        assert hash1 != hash4
    
    def test_hash_face_embedding(self, encryption_manager, sample_face_embedding):
        """Test face embedding hashing."""
        hash1 = encryption_manager.hash_face_embedding(sample_face_embedding)
        hash2 = encryption_manager.hash_face_embedding(sample_face_embedding)
        
        assert hash1 == hash2  # Same embedding should produce same hash
        assert len(hash1) == 64  # SHA-256 hex string
        
        # Different embedding should produce different hash
        different_embedding = np.random.rand(512).astype(np.float32)
        hash3 = encryption_manager.hash_face_embedding(different_embedding)
        assert hash1 != hash3


class TestFaceEmbeddingStorage:
    """Test FaceEmbeddingStorage functionality."""
    
    def test_store_embedding(self, face_embedding_storage, sample_face_embedding):
        """Test storing face embedding."""
        student_id = "STU001"
        
        storage_data = face_embedding_storage.store_embedding(student_id, sample_face_embedding)
        
        assert storage_data["student_id"] == student_id
        assert "encrypted_embedding" in storage_data
        assert "embedding_hash" in storage_data
        assert "embedding_size" in storage_data
        assert "original_shape" in storage_data
        assert "original_dtype" in storage_data
        
        assert isinstance(storage_data["encrypted_embedding"], bytes)
        assert len(storage_data["embedding_hash"]) == 64
        assert storage_data["embedding_size"] > 0
        assert storage_data["original_shape"] == sample_face_embedding.shape
        assert storage_data["original_dtype"] == str(sample_face_embedding.dtype)
    
    def test_retrieve_embedding(self, face_embedding_storage, sample_face_embedding):
        """Test retrieving face embedding."""
        student_id = "STU001"
        
        # Store embedding
        storage_data = face_embedding_storage.store_embedding(student_id, sample_face_embedding)
        encrypted_embedding = storage_data["encrypted_embedding"]
        
        # Retrieve embedding
        retrieved_embedding = face_embedding_storage.retrieve_embedding(encrypted_embedding)
        
        assert isinstance(retrieved_embedding, np.ndarray)
        assert retrieved_embedding.shape == sample_face_embedding.shape
        assert retrieved_embedding.dtype == sample_face_embedding.dtype
        np.testing.assert_array_equal(retrieved_embedding, sample_face_embedding)
    
    def test_compare_embeddings(self, face_embedding_storage, sample_face_embedding):
        """Test embedding comparison."""
        # Same embeddings should have high similarity
        similarity1 = face_embedding_storage.compare_embeddings(sample_face_embedding, sample_face_embedding)
        assert similarity1 == 1.0  # Perfect similarity
        
        # Different embeddings should have lower similarity
        different_embedding = np.random.rand(512).astype(np.float32)
        similarity2 = face_embedding_storage.compare_embeddings(sample_face_embedding, different_embedding)
        assert 0.0 <= similarity2 <= 1.0
        assert similarity2 < 1.0
        
        # Similar embeddings should have high similarity
        similar_embedding = sample_face_embedding + np.random.normal(0, 0.01, sample_face_embedding.shape).astype(np.float32)
        similarity3 = face_embedding_storage.compare_embeddings(sample_face_embedding, similar_embedding)
        assert similarity3 > 0.8  # Should be quite similar
    
    def test_calculate_distance(self, face_embedding_storage, sample_face_embedding):
        """Test embedding distance calculation."""
        # Same embeddings should have zero distance
        distance1 = face_embedding_storage.calculate_distance(sample_face_embedding, sample_face_embedding)
        assert distance1 == 0.0
        
        # Different embeddings should have positive distance
        different_embedding = np.random.rand(512).astype(np.float32)
        distance2 = face_embedding_storage.calculate_distance(sample_face_embedding, different_embedding)
        assert distance2 > 0.0
        
        # Similar embeddings should have small distance
        similar_embedding = sample_face_embedding + np.random.normal(0, 0.01, sample_face_embedding.shape).astype(np.float32)
        distance3 = face_embedding_storage.calculate_distance(sample_face_embedding, similar_embedding)
        assert distance3 < distance2  # Should be smaller than completely different embedding
    
    def test_compare_zero_embeddings(self, face_embedding_storage):
        """Test comparison with zero embeddings."""
        zero_embedding = np.zeros(512, dtype=np.float32)
        normal_embedding = np.random.rand(512).astype(np.float32)
        
        # Zero embedding comparison should return 0
        similarity = face_embedding_storage.compare_embeddings(zero_embedding, normal_embedding)
        assert similarity == 0.0
    
    def test_embedding_storage_error_handling(self, face_embedding_storage):
        """Test error handling in embedding storage."""
        # Test with invalid encrypted data
        invalid_encrypted_data = b"invalid_data"
        
        with pytest.raises(Exception):
            face_embedding_storage.retrieve_embedding(invalid_encrypted_data)
    
    def test_multiple_embeddings_storage(self, face_embedding_storage):
        """Test storing and retrieving multiple embeddings."""
        embeddings = {
            "STU001": np.random.rand(512).astype(np.float32),
            "STU002": np.random.rand(512).astype(np.float32),
            "STU003": np.random.rand(512).astype(np.float32)
        }
        
        stored_data = {}
        for student_id, embedding in embeddings.items():
            storage_data = face_embedding_storage.store_embedding(student_id, embedding)
            stored_data[student_id] = storage_data["encrypted_embedding"]
        
        # Retrieve and verify all embeddings
        for student_id, original_embedding in embeddings.items():
            encrypted_embedding = stored_data[student_id]
            retrieved_embedding = face_embedding_storage.retrieve_embedding(encrypted_embedding)
            np.testing.assert_array_equal(retrieved_embedding, original_embedding)
    
    def test_embedding_consistency(self, face_embedding_storage, sample_face_embedding):
        """Test that multiple encryptions of same embedding can be decrypted correctly."""
        student_id = "STU001"
        
        # Store same embedding multiple times
        storage_data1 = face_embedding_storage.store_embedding(student_id, sample_face_embedding)
        storage_data2 = face_embedding_storage.store_embedding(student_id, sample_face_embedding)
        
        # Encrypted data should be different (due to encryption randomness)
        assert storage_data1["encrypted_embedding"] != storage_data2["encrypted_embedding"]
        
        # But hashes should be the same
        assert storage_data1["embedding_hash"] == storage_data2["embedding_hash"]
        
        # Both should decrypt to the same original embedding
        retrieved1 = face_embedding_storage.retrieve_embedding(storage_data1["encrypted_embedding"])
        retrieved2 = face_embedding_storage.retrieve_embedding(storage_data2["encrypted_embedding"])
        
        np.testing.assert_array_equal(retrieved1, sample_face_embedding)
        np.testing.assert_array_equal(retrieved2, sample_face_embedding)
        np.testing.assert_array_equal(retrieved1, retrieved2)