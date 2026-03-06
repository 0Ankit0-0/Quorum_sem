"""
Settings Service
Storage quota management, encryption config, and secure system log export.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Dict
import zipfile

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend

from config.settings import settings
from config.logging_config import get_logger
from core.security import CryptoUtils

logger = get_logger(__name__)


class SettingsService:
    def __init__(self):
        self.settings_dir = settings.DATA_DIR / "settings"
        self.settings_dir.mkdir(parents=True, exist_ok=True)
        self.storage_cfg_path = self.settings_dir / "storage.json"
        self.encryption_cfg_path = self.settings_dir / "encryption.json"
        self.passphrase_hash_path = self.settings_dir / "passphrase.sha256"
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        if not self.storage_cfg_path.exists():
            self.storage_cfg_path.write_text(
                json.dumps({"max_gb": 4.0}, indent=2),
                encoding="utf-8",
            )
        if not self.encryption_cfg_path.exists():
            self.encryption_cfg_path.write_text(
                json.dumps(
                    {
                        "signature_algorithm": "RSA-PSS-4096",
                        "hash_algorithm": "SHA-256",
                        "key_rotation_days": 90,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
        if not self.passphrase_hash_path.exists():
            self.set_export_passphrase("quorum-admin")

    def set_export_passphrase(self, passphrase: str) -> None:
        digest = hashlib.sha256(passphrase.encode("utf-8")).hexdigest()
        self.passphrase_hash_path.write_text(digest, encoding="utf-8")

    def verify_passphrase(self, passphrase: str) -> bool:
        expected = self.passphrase_hash_path.read_text(encoding="utf-8").strip()
        actual = hashlib.sha256(passphrase.encode("utf-8")).hexdigest()
        return actual == expected

    def get_storage_status(self) -> Dict[str, Any]:
        cfg = json.loads(self.storage_cfg_path.read_text(encoding="utf-8"))
        quota_bytes = int(float(cfg.get("max_gb", 4.0)) * 1024 * 1024 * 1024)

        categories = {
            "logs": settings.LOGS_DIR,
            "databases": settings.DB_DIR,
            "reports": settings.REPORTS_DIR,
            "models": settings.MODELS_DIR,
        }
        usage = {name: self._dir_size(path) for name, path in categories.items()}
        total_used = sum(usage.values())
        ratio = total_used / max(quota_bytes, 1)
        alert = "normal"
        if ratio >= 0.95:
            alert = "critical"
        elif ratio >= 0.80:
            alert = "warning"

        suggestions = []
        if usage["reports"] > 0:
            suggestions.append("Archive or delete old report folders.")
        if usage["logs"] > 0:
            suggestions.append("Rotate quorum.log and keep compressed history.")
        if usage["databases"] > 0:
            suggestions.append("Prune unused dataset databases.")

        return {
            "quota_bytes": quota_bytes,
            "used_bytes": total_used,
            "usage_by_category": usage,
            "utilization_percent": round(ratio * 100, 2),
            "alert_level": alert,
            "cleanup_suggestions": suggestions,
        }

    def update_storage_quota(self, max_gb: float) -> Dict[str, Any]:
        max_gb = max(0.5, min(max_gb, 2048.0))
        self.storage_cfg_path.write_text(
            json.dumps({"max_gb": max_gb}, indent=2),
            encoding="utf-8",
        )
        return self.get_storage_status()

    def get_encryption_config(self) -> Dict[str, Any]:
        return json.loads(self.encryption_cfg_path.read_text(encoding="utf-8"))

    def update_encryption_config(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_encryption_config()
        current.update(payload)
        self.encryption_cfg_path.write_text(
            json.dumps(current, indent=2),
            encoding="utf-8",
        )
        return current

    def export_system_log(
        self,
        passphrase: str,
        encrypt: bool = False,
    ) -> Dict[str, Any]:
        if not self.verify_passphrase(passphrase):
            raise PermissionError("Invalid passphrase")

        log_path = settings.LOGS_DIR / settings.LOG_FILE
        if not log_path.exists():
            raise FileNotFoundError("System log not found")

        output_dir = settings.DATA_DIR / "exports"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        raw_log = log_path.read_bytes()
        log_hash = hashlib.sha256(raw_log).hexdigest()
        signature = self._sign_blob(raw_log)

        package_path = output_dir / f"quorum_log_{timestamp}.zip"
        with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("quorum.log", raw_log)
            zf.writestr("quorum.log.sha256", log_hash)
            zf.writestr("quorum.log.sig", signature.hex())
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "created_at": datetime.utcnow().isoformat(),
                        "file": "quorum.log",
                        "sha256": log_hash,
                        "signature_algorithm": "RSA-PSS-SHA256",
                    },
                    indent=2,
                ),
            )

        exported = package_path
        if encrypt:
            encrypted_path = output_dir / f"{package_path.stem}.enc"
            encrypted_path.write_bytes(self._encrypt_blob(package_path.read_bytes(), passphrase))
            package_path.unlink(missing_ok=True)
            exported = encrypted_path

        return {
            "filename": exported.name,
            "path": str(exported),
            "sha256": hashlib.sha256(exported.read_bytes()).hexdigest(),
            "encrypted": encrypt,
            "size_bytes": exported.stat().st_size,
        }

    def _encrypt_blob(self, data: bytes, passphrase: str) -> bytes:
        salt = hashlib.sha256(passphrase.encode("utf-8")).digest()[:16]
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
            backend=default_backend(),
        )
        key = Fernet(base64_urlsafe(kdf.derive(passphrase.encode("utf-8"))))
        return key.encrypt(data)

    def _sign_blob(self, data: bytes) -> bytes:
        key_path = settings.KEYS_DIR / "private_key.pem"
        if not key_path.exists():
            return b""
        return CryptoUtils.sign_data(key_path.read_bytes(), data)

    def _dir_size(self, path: Path) -> int:
        if not path.exists():
            return 0
        total = 0
        for file_path in path.rglob("*"):
            if file_path.is_file():
                try:
                    total += file_path.stat().st_size
                except Exception:
                    continue
        return total


def base64_urlsafe(raw: bytes) -> bytes:
    import base64

    return base64.urlsafe_b64encode(raw)


settings_service = SettingsService()

