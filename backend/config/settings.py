"""
Configuration Management
Handles all application settings with environment variable support
"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    APP_NAME: str = "Quorum"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_DIR: Path = DATA_DIR / "databases"
    MODELS_DIR: Path = DATA_DIR / "models"
    KEYS_DIR: Path = DATA_DIR / "keys"
    MITRE_DIR: Path = DATA_DIR / "mitre_attack"
    LOGS_DIR: Path = BASE_DIR / "logs"
    REPORTS_DIR: Path = BASE_DIR / "reports_output"
    
    # Database
    DB_NAME: str = "quorum.duckdb"
    DB_MEMORY: bool = False  # Use file-based DB by default
    DB_THREADS: int = 4
    DB_MAX_MEMORY: str = "4GB"
    
    # API
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_RELOAD: bool = False
    API_WORKERS: int = 1
    
    # AI Engine
    AI_ANOMALY_THRESHOLD: float = 0.95  # 95th percentile
    AI_CONTAMINATION: float = 0.01  # 1% expected anomalies
    AI_RANDOM_SEED: int = 42
    AI_N_JOBS: int = -1  # Use all cores
    AI_SVM_MAX_SAMPLES: int = 10000
    AI_LARGE_DATASET_THRESHOLD: int = 100000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    LOG_FILE: str = "quorum.log"
    
    # Security (SOUP)
    SOUP_PUBLIC_KEY: str = "public_key.pem"
    SOUP_SIGNATURE_ALGORITHM: str = "RSA-PSS"
    SOUP_HASH_ALGORITHM: str = "SHA256"
    
    # Performance
    BATCH_SIZE: int = 10000
    MAX_WORKERS: int = 4
    CHUNK_SIZE: int = 1000
    
    # MITRE ATT&CK
    MITRE_VERSION: str = "14.1"
    MITRE_FRAMEWORK: str = "enterprise-attack"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._create_directories()
    
    def _create_directories(self):
        """Create necessary directories if they don't exist"""
        for dir_path in [
            self.DATA_DIR,
            self.DB_DIR,
            self.MODELS_DIR,
            self.KEYS_DIR,
            self.MITRE_DIR,
            self.LOGS_DIR,
            self.REPORTS_DIR
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @property
    def database_path(self) -> Path:
        """Get full database path"""
        return self.DB_DIR / self.DB_NAME
    
    @property
    def public_key_path(self) -> Path:
        """Get public key path"""
        return self.KEYS_DIR / self.SOUP_PUBLIC_KEY


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
