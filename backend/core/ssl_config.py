"""
SSL/TLS configuration and certificate management for the Smart Attendance System.
"""

import os
import ssl
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class SSLConfig:
    """SSL/TLS configuration."""
    cert_file: str
    key_file: str
    ca_file: Optional[str] = None
    verify_mode: int = ssl.CERT_REQUIRED
    check_hostname: bool = True
    protocol: int = ssl.PROTOCOL_TLS_SERVER
    ciphers: Optional[str] = None


class CertificateManager:
    """Manages SSL/TLS certificates for the system."""
    
    def __init__(self, cert_dir: str = "certs"):
        """Initialize certificate manager."""
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(exist_ok=True)
        
        # Default certificate paths
        self.ca_cert_path = self.cert_dir / "ca.crt"
        self.ca_key_path = self.cert_dir / "ca.key"
        self.server_cert_path = self.cert_dir / "server.crt"
        self.server_key_path = self.cert_dir / "server.key"
        self.client_cert_path = self.cert_dir / "client.crt"
        self.client_key_path = self.cert_dir / "client.key"
    
    def generate_ca_certificate(self, 
                               common_name: str = "Smart Attendance CA",
                               validity_days: int = 3650) -> tuple:
        """Generate Certificate Authority certificate and key."""
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
            )
            
            # Create certificate
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Smart Attendance System"),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=validity_days)
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.DNSName("smart-attendance-ca"),
                ]),
                critical=False,
            ).add_extension(
                x509.BasicConstraints(ca=True, path_length=None),
                critical=True,
            ).add_extension(
                x509.KeyUsage(
                    key_cert_sign=True,
                    crl_sign=True,
                    digital_signature=False,
                    key_encipherment=False,
                    key_agreement=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            ).sign(private_key, hashes.SHA256())
            
            # Save certificate and key
            with open(self.ca_cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            with open(self.ca_key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            logger.info(f"CA certificate generated: {self.ca_cert_path}")
            return cert, private_key
            
        except Exception as e:
            logger.error(f"Failed to generate CA certificate: {e}")
            raise
    
    def generate_server_certificate(self,
                                   common_name: str = "smart-attendance-server",
                                   san_list: list = None,
                                   validity_days: int = 365) -> tuple:
        """Generate server certificate signed by CA."""
        try:
            if not self.ca_cert_path.exists() or not self.ca_key_path.exists():
                logger.info("CA certificate not found, generating new CA")
                self.generate_ca_certificate()
            
            # Load CA certificate and key
            with open(self.ca_cert_path, "rb") as f:
                ca_cert = x509.load_pem_x509_certificate(f.read())
            
            with open(self.ca_key_path, "rb") as f:
                ca_key = serialization.load_pem_private_key(f.read(), password=None)
            
            # Generate server private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Default SAN list
            if san_list is None:
                san_list = [
                    "localhost",
                    "127.0.0.1",
                    "smart-attendance-api",
                    "api_gateway",
                    "face_recognition_service",
                    "emotion_analysis_service",
                    "attendance_service",
                    "validation_service",
                    "websocket_server"
                ]
            
            # Create certificate
            subject = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Smart Attendance System"),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ])
            
            # Build SAN extension
            san_names = []
            for name in san_list:
                try:
                    # Try to parse as IP address
                    import ipaddress
                    ip = ipaddress.ip_address(name)
                    san_names.append(x509.IPAddress(ip))
                except ValueError:
                    # It's a DNS name
                    san_names.append(x509.DNSName(name))
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                ca_cert.subject
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=validity_days)
            ).add_extension(
                x509.SubjectAlternativeName(san_names),
                critical=False,
            ).add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            ).add_extension(
                x509.KeyUsage(
                    key_cert_sign=False,
                    crl_sign=False,
                    digital_signature=True,
                    key_encipherment=True,
                    key_agreement=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            ).add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                ]),
                critical=True,
            ).sign(ca_key, hashes.SHA256())
            
            # Save certificate and key
            with open(self.server_cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            with open(self.server_key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            logger.info(f"Server certificate generated: {self.server_cert_path}")
            return cert, private_key
            
        except Exception as e:
            logger.error(f"Failed to generate server certificate: {e}")
            raise
    
    def generate_client_certificate(self,
                                   common_name: str = "smart-attendance-client",
                                   validity_days: int = 365) -> tuple:
        """Generate client certificate for mutual TLS authentication."""
        try:
            if not self.ca_cert_path.exists() or not self.ca_key_path.exists():
                logger.info("CA certificate not found, generating new CA")
                self.generate_ca_certificate()
            
            # Load CA certificate and key
            with open(self.ca_cert_path, "rb") as f:
                ca_cert = x509.load_pem_x509_certificate(f.read())
            
            with open(self.ca_key_path, "rb") as f:
                ca_key = serialization.load_pem_private_key(f.read(), password=None)
            
            # Generate client private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # Create certificate
            subject = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Smart Attendance System"),
                x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            ])
            
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                ca_cert.subject
            ).public_key(
                private_key.public_key()
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.utcnow()
            ).not_valid_after(
                datetime.utcnow() + timedelta(days=validity_days)
            ).add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            ).add_extension(
                x509.KeyUsage(
                    key_cert_sign=False,
                    crl_sign=False,
                    digital_signature=True,
                    key_encipherment=True,
                    key_agreement=False,
                    content_commitment=False,
                    data_encipherment=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            ).add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                ]),
                critical=True,
            ).sign(ca_key, hashes.SHA256())
            
            # Save certificate and key
            with open(self.client_cert_path, "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))
            
            with open(self.client_key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            logger.info(f"Client certificate generated: {self.client_cert_path}")
            return cert, private_key
            
        except Exception as e:
            logger.error(f"Failed to generate client certificate: {e}")
            raise
    
    def get_ssl_context(self, 
                       context_type: str = "server",
                       verify_mode: int = ssl.CERT_REQUIRED) -> ssl.SSLContext:
        """Create SSL context for server or client."""
        try:
            if context_type == "server":
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                context.load_cert_chain(str(self.server_cert_path), str(self.server_key_path))
                
                if self.ca_cert_path.exists():
                    context.load_verify_locations(str(self.ca_cert_path))
                    context.verify_mode = verify_mode
                
            elif context_type == "client":
                context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                
                if self.ca_cert_path.exists():
                    context.load_verify_locations(str(self.ca_cert_path))
                
                if self.client_cert_path.exists() and self.client_key_path.exists():
                    context.load_cert_chain(str(self.client_cert_path), str(self.client_key_path))
                
                context.verify_mode = verify_mode
                context.check_hostname = True
            
            else:
                raise ValueError(f"Invalid context type: {context_type}")
            
            # Security settings
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
            
            logger.debug(f"SSL context created for {context_type}")
            return context
            
        except Exception as e:
            logger.error(f"Failed to create SSL context: {e}")
            raise
    
    def verify_certificate(self, cert_path: str) -> Dict[str, Any]:
        """Verify certificate and return information."""
        try:
            with open(cert_path, "rb") as f:
                cert = x509.load_pem_x509_certificate(f.read())
            
            # Extract certificate information
            info = {
                "subject": cert.subject.rfc4514_string(),
                "issuer": cert.issuer.rfc4514_string(),
                "serial_number": str(cert.serial_number),
                "not_valid_before": cert.not_valid_before,
                "not_valid_after": cert.not_valid_after,
                "is_expired": cert.not_valid_after < datetime.utcnow(),
                "days_until_expiry": (cert.not_valid_after - datetime.utcnow()).days,
                "signature_algorithm": cert.signature_algorithm_oid._name,
            }
            
            # Extract SAN
            try:
                san_ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                info["subject_alternative_names"] = [name.value for name in san_ext.value]
            except x509.ExtensionNotFound:
                info["subject_alternative_names"] = []
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to verify certificate {cert_path}: {e}")
            raise
    
    def setup_certificates(self, force_regenerate: bool = False):
        """Setup all required certificates."""
        try:
            # Check if certificates exist and are valid
            need_ca = force_regenerate or not self.ca_cert_path.exists()
            need_server = force_regenerate or not self.server_cert_path.exists()
            need_client = force_regenerate or not self.client_cert_path.exists()
            
            # Check certificate expiry
            if not need_server and self.server_cert_path.exists():
                try:
                    cert_info = self.verify_certificate(str(self.server_cert_path))
                    if cert_info["days_until_expiry"] < 30:
                        logger.warning("Server certificate expires in less than 30 days, regenerating")
                        need_server = True
                        need_ca = True  # Regenerate CA as well
                except Exception:
                    need_server = True
            
            if need_ca:
                logger.info("Generating CA certificate")
                self.generate_ca_certificate()
            
            if need_server:
                logger.info("Generating server certificate")
                self.generate_server_certificate()
            
            if need_client:
                logger.info("Generating client certificate")
                self.generate_client_certificate()
            
            logger.info("Certificate setup completed")
            
        except Exception as e:
            logger.error(f"Failed to setup certificates: {e}")
            raise


# Global certificate manager instance
_cert_manager = None


def get_certificate_manager() -> CertificateManager:
    """Get global certificate manager instance."""
    global _cert_manager
    if _cert_manager is None:
        cert_dir = os.getenv("SSL_CERT_DIR", "certs")
        _cert_manager = CertificateManager(cert_dir)
    return _cert_manager


def get_ssl_config() -> SSLConfig:
    """Get SSL configuration from environment."""
    cert_manager = get_certificate_manager()
    
    return SSLConfig(
        cert_file=str(cert_manager.server_cert_path),
        key_file=str(cert_manager.server_key_path),
        ca_file=str(cert_manager.ca_cert_path) if cert_manager.ca_cert_path.exists() else None,
        verify_mode=ssl.CERT_REQUIRED if os.getenv("SSL_VERIFY_CLIENT", "false").lower() == "true" else ssl.CERT_NONE,
        check_hostname=os.getenv("SSL_CHECK_HOSTNAME", "true").lower() == "true",
        ciphers=os.getenv("SSL_CIPHERS")
    )