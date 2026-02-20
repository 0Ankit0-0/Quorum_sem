"""
Security Module - SOUP (Secure Offline Update Protocol)
Handles cryptographic operations for secure updates
"""
from pathlib import Path
from typing import Optional, Tuple
import hashlib
import json
from datetime import datetime
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

from config.settings import settings
from core.exceptions import SecurityError
from config.logging_config import get_logger

logger = get_logger(__name__)


class SOUPManager:
    """Secure Offline Update Protocol Manager"""
    
    def __init__(self):
        self.public_key_path = settings.public_key_path
        self.public_key = None
        self._load_public_key()
    
    def _load_public_key(self):
        """Load public key for signature verification"""
        try:
            if self.public_key_path.exists():
                with open(self.public_key_path, 'rb') as f:
                    self.public_key = serialization.load_pem_public_key(
                        f.read(),
                        backend=default_backend()
                    )
                logger.info("Public key loaded successfully")
            else:
                logger.warning(f"Public key not found at {self.public_key_path}")
        except Exception as e:
            logger.error(f"Failed to load public key: {e}")
            raise SecurityError(f"Public key loading failed: {e}")
    
    def verify_update_package(self, package_path: Path) -> Tuple[bool, str]:
        """
        Verify update package signature and integrity
        
        Args:
            package_path: Path to update package (.qup file)
        
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            logger.info(f"Verifying update package: {package_path}")
            
            if not package_path.exists():
                return False, "Package file not found"
            
            # Read package
            with open(package_path, 'rb') as f:
                package_data = f.read()
            
            # Parse package (JSON format)
            try:
                package_json = json.loads(package_data.decode('utf-8'))
            except json.JSONDecodeError:
                return False, "Invalid package format"
            
            # Extract components
            payload = package_json.get('payload')
            signature_b64 = package_json.get('signature')
            declared_hash = package_json.get('hash')
            metadata = package_json.get('metadata', {})
            
            if not all([payload, signature_b64, declared_hash]):
                return False, "Missing required package components"
            
            # Verify hash
            payload_bytes = payload.encode('utf-8')
            computed_hash = hashlib.sha256(payload_bytes).hexdigest()
            
            if computed_hash != declared_hash:
                logger.warning("Hash verification failed")
                return False, "Package integrity check failed (hash mismatch)"
            
            logger.info("Hash verification passed")
            
            # Verify signature
            if self.public_key is None:
                return False, "Public key not available for verification"
            
            try:
                import base64
                signature_bytes = base64.b64decode(signature_b64)
                
                self.public_key.verify(
                    signature_bytes,
                    payload_bytes,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                
                logger.info("Signature verification passed")
                
            except InvalidSignature:
                logger.warning("Signature verification failed")
                return False, "Invalid signature - package may be tampered"
            
            # Log verification success
            logger.info(f"Update package verified successfully: {metadata.get('version', 'unknown')}")
            
            return True, "Package verified successfully"
        
        except Exception as e:
            logger.error(f"Update verification error: {e}")
            return False, f"Verification error: {str(e)}"
    
    def extract_update_payload(self, package_path: Path) -> dict:
        """
        Extract payload from verified update package
        
        Args:
            package_path: Path to verified update package
        
        Returns:
            Payload dictionary
        """
        try:
            with open(package_path, 'rb') as f:
                package_data = json.loads(f.read().decode('utf-8'))
            
            payload_str = package_data.get('payload')
            payload = json.loads(payload_str)
            
            logger.info(f"Extracted payload: {payload.get('type', 'unknown')}")
            return payload
        
        except Exception as e:
            logger.error(f"Payload extraction failed: {e}")
            raise SecurityError(f"Failed to extract payload: {e}")
    
    def log_update_applied(self, package_info: dict):
        """
        Log applied update for audit trail
        
        Args:
            package_info: Update package information
        """
        try:
            update_log_path = settings.DATA_DIR / "update_history.json"
            
            # Load existing history
            history = []
            if update_log_path.exists():
                with open(update_log_path, 'r') as f:
                    history = json.load(f)
            
            # Add new entry
            history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'version': package_info.get('version'),
                'type': package_info.get('type'),
                'hash': package_info.get('hash'),
                'metadata': package_info.get('metadata', {})
            })
            
            # Save updated history
            with open(update_log_path, 'w') as f:
                json.dump(history, f, indent=2)
            
            logger.info(f"Update logged: {package_info.get('version')}")
        
        except Exception as e:
            logger.error(f"Failed to log update: {e}")
    
    def get_update_history(self) -> list:
        """Get list of applied updates"""
        try:
            update_log_path = settings.DATA_DIR / "update_history.json"
            
            if not update_log_path.exists():
                return []
            
            with open(update_log_path, 'r') as f:
                return json.load(f)
        
        except Exception as e:
            logger.error(f"Failed to retrieve update history: {e}")
            return []


class CryptoUtils:
    """Cryptographic utility functions"""
    
    @staticmethod
    def generate_key_pair(key_size: int = 2048) -> Tuple[bytes, bytes]:
        """
        Generate RSA key pair
        
        Args:
            key_size: Key size in bits (default 2048)
        
        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            
            # Serialize private key
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Get public key
            public_key = private_key.public_key()
            
            # Serialize public key
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            logger.info(f"Generated {key_size}-bit RSA key pair")
            return private_pem, public_pem
        
        except Exception as e:
            logger.error(f"Key generation failed: {e}")
            raise SecurityError(f"Failed to generate key pair: {e}")
    
    @staticmethod
    def compute_file_hash(file_path: Path, algorithm: str = 'sha256') -> str:
        """
        Compute hash of file
        
        Args:
            file_path: Path to file
            algorithm: Hash algorithm ('sha256', 'sha512', 'md5')
        
        Returns:
            Hex digest of hash
        """
        try:
            hash_func = getattr(hashlib, algorithm)()
            
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    hash_func.update(chunk)
            
            return hash_func.hexdigest()
        
        except Exception as e:
            logger.error(f"Hash computation failed: {e}")
            raise SecurityError(f"Failed to compute hash: {e}")
    
    @staticmethod
    def sign_data(private_key_pem: bytes, data: bytes) -> bytes:
        """
        Sign data with private key
        
        Args:
            private_key_pem: Private key in PEM format
            data: Data to sign
        
        Returns:
            Signature bytes
        """
        try:
            private_key = serialization.load_pem_private_key(
                private_key_pem,
                password=None,
                backend=default_backend()
            )
            
            signature = private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return signature
        
        except Exception as e:
            logger.error(f"Data signing failed: {e}")
            raise SecurityError(f"Failed to sign data: {e}")


# Global SOUP manager instance
soup_manager = SOUPManager()