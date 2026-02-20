"""
Update Service
Handles SOUP (Secure Offline Update Protocol) operations
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import shutil
import json

from core.security import soup_manager
from core.exceptions import UpdateError, SecurityError
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


class UpdateService:
    """Service for managing secure offline updates"""
    
    def __init__(self):
        self.updates_dir = settings.DATA_DIR / "updates"
        self.updates_dir.mkdir(exist_ok=True)
    
    def verify_update(self, package_path: Path) -> Dict[str, Any]:
        """
        Verify update package
        
        Args:
            package_path: Path to update package (.qup file)
        
        Returns:
            Verification result
        """
        package_path = Path(package_path)
        
        logger.info(f"Verifying update package: {package_path}")
        
        is_valid, message = soup_manager.verify_update_package(package_path)
        
        result = {
            'valid': is_valid,
            'message': message,
            'package_path': str(package_path)
        }
        
        if is_valid:
            # Extract metadata
            try:
                payload = soup_manager.extract_update_payload(package_path)
                result['metadata'] = payload.get('metadata', {})
                result['version'] = payload.get('version', 'unknown')
                result['type'] = payload.get('type', 'unknown')
            except Exception as e:
                logger.error(f"Failed to extract metadata: {e}")
                result['metadata'] = {}
        
        return result
    
    def apply_update(self, package_path: Path) -> Dict[str, Any]:
        """
        Apply verified update package
        
        Args:
            package_path: Path to verified update package
        
        Returns:
            Application result
        """
        package_path = Path(package_path)
        
        logger.info(f"Applying update from: {package_path}")
        
        # Verify first
        verification = self.verify_update(package_path)
        
        if not verification['valid']:
            raise UpdateError(f"Update verification failed: {verification['message']}")
        
        try:
            # Extract payload
            payload = soup_manager.extract_update_payload(package_path)
            
            update_type = payload.get('type')
            
            if update_type == 'model':
                result = self._apply_model_update(payload)
            elif update_type == 'rules':
                result = self._apply_rules_update(payload)
            elif update_type == 'mitre':
                result = self._apply_mitre_update(payload)
            else:
                raise UpdateError(f"Unknown update type: {update_type}")
            
            # Log update
            soup_manager.log_update_applied({
                'version': payload.get('version'),
                'type': update_type,
                'hash': payload.get('hash'),
                'metadata': payload.get('metadata', {})
            })
            
            logger.info(f"Update applied successfully: {update_type}")
            
            return {
                'success': True,
                'type': update_type,
                'version': payload.get('version'),
                'message': result.get('message', 'Update applied successfully')
            }
        
        except Exception as e:
            logger.error(f"Failed to apply update: {e}")
            raise UpdateError(f"Update application failed: {e}")
    
    def _apply_model_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply ML model update"""
        try:
            model_data = payload.get('data', {})
            model_type = model_data.get('model_type')
            model_file = model_data.get('model_file')
            
            if not model_type or not model_file:
                raise UpdateError("Invalid model update payload")
            
            # Backup existing model
            existing_model = settings.MODELS_DIR / f"{model_type}.pkl"
            if existing_model.exists():
                backup_path = settings.MODELS_DIR / f"{model_type}_backup.pkl"
                shutil.copy(existing_model, backup_path)
                logger.info(f"Backed up existing model to {backup_path}")
            
            # Save new model
            import base64
            model_bytes = base64.b64decode(model_file)
            
            new_model_path = settings.MODELS_DIR / f"{model_type}.pkl"
            with open(new_model_path, 'wb') as f:
                f.write(model_bytes)
            
            logger.info(f"Saved new {model_type} model")
            
            return {'message': f'Model {model_type} updated successfully'}
        
        except Exception as e:
            logger.error(f"Model update failed: {e}")
            raise UpdateError(f"Model update failed: {e}")
    
    def _apply_rules_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply detection rules update"""
        try:
            rules_data = payload.get('data', {})
            rules = rules_data.get('rules', [])
            
            if not rules:
                raise UpdateError("No rules in update payload")
            
            # Save rules
            rules_file = settings.DATA_DIR / "detection_rules.json"
            
            # Backup existing rules
            if rules_file.exists():
                backup_path = settings.DATA_DIR / "detection_rules_backup.json"
                shutil.copy(rules_file, backup_path)
            
            # Write new rules
            with open(rules_file, 'w') as f:
                json.dump(rules, f, indent=2)
            
            logger.info(f"Updated {len(rules)} detection rules")
            
            return {'message': f'{len(rules)} detection rules updated'}
        
        except Exception as e:
            logger.error(f"Rules update failed: {e}")
            raise UpdateError(f"Rules update failed: {e}")
    
    def _apply_mitre_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply MITRE ATT&CK data update"""
        try:
            mitre_data = payload.get('data', {})
            attack_data = mitre_data.get('attack_data')
            
            if not attack_data:
                raise UpdateError("No MITRE data in update payload")
            
            # Backup existing data
            if settings.MITRE_DIR.exists():
                backup_path = settings.DATA_DIR / "mitre_backup"
                if backup_path.exists():
                    shutil.rmtree(backup_path)
                shutil.copytree(settings.MITRE_DIR, backup_path)
            
            # Write new data
            settings.MITRE_DIR.mkdir(exist_ok=True)
            mitre_file = settings.MITRE_DIR / "enterprise-attack.json"
            
            with open(mitre_file, 'w') as f:
                json.dump(attack_data, f, indent=2)
            
            # Reload MITRE data
            from services.mitre_service import mitre_service
            count = mitre_service.load_mitre_data()
            
            logger.info(f"Updated MITRE ATT&CK data: {count} techniques")
            
            return {'message': f'MITRE ATT&CK data updated: {count} techniques'}
        
        except Exception as e:
            logger.error(f"MITRE update failed: {e}")
            raise UpdateError(f"MITRE update failed: {e}")
    
    def rollback_update(self, update_type: str) -> Dict[str, Any]:
        """
        Rollback to previous version
        
        Args:
            update_type: Type of update to rollback ('model', 'rules', 'mitre')
        
        Returns:
            Rollback result
        """
        logger.info(f"Rolling back {update_type} update")
        
        try:
            if update_type == 'model':
                # Find backup models
                backups = list(settings.MODELS_DIR.glob("*_backup.pkl"))
                
                for backup in backups:
                    original_name = backup.name.replace('_backup', '')
                    original_path = settings.MODELS_DIR / original_name
                    
                    shutil.copy(backup, original_path)
                    logger.info(f"Restored {original_name}")
                
                return {'success': True, 'message': f'Rolled back {len(backups)} model(s)'}
            
            elif update_type == 'rules':
                backup_path = settings.DATA_DIR / "detection_rules_backup.json"
                rules_path = settings.DATA_DIR / "detection_rules.json"
                
                if backup_path.exists():
                    shutil.copy(backup_path, rules_path)
                    logger.info("Restored detection rules")
                    return {'success': True, 'message': 'Detection rules rolled back'}
                else:
                    return {'success': False, 'message': 'No backup found'}
            
            elif update_type == 'mitre':
                backup_path = settings.DATA_DIR / "mitre_backup"
                
                if backup_path.exists():
                    if settings.MITRE_DIR.exists():
                        shutil.rmtree(settings.MITRE_DIR)
                    shutil.copytree(backup_path, settings.MITRE_DIR)
                    
                    # Reload MITRE data
                    from services.mitre_service import mitre_service
                    count = mitre_service.load_mitre_data()
                    
                    logger.info("Restored MITRE ATT&CK data")
                    return {'success': True, 'message': f'MITRE data rolled back: {count} techniques'}
                else:
                    return {'success': False, 'message': 'No backup found'}
            
            else:
                raise UpdateError(f"Unknown update type: {update_type}")
        
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            raise UpdateError(f"Rollback failed: {e}")
    
    def get_update_history(self) -> List[Dict[str, Any]]:
        """Get history of applied updates"""
        return soup_manager.get_update_history()
    
    def scan_for_updates(self) -> List[Path]:
        """
        Scan for update packages on connected devices
        
        Returns:
            List of update package paths found
        """
        from core.environment import env_detector
        
        logger.info("Scanning for update packages...")
        
        update_packages = []
        
        # Get connected devices
        env_info = env_detector.detect_all()
        devices = env_info.get('connected_devices', [])
        usb_devices = env_info.get('usb_devices', [])
        
        # Scan each device
        for device in devices + usb_devices:
            mountpoint = device.get('mountpoint')
            if not mountpoint:
                continue
            
            try:
                mount_path = Path(mountpoint)
                
                # Look for .qup files
                for qup_file in mount_path.rglob("*.qup"):
                    if qup_file.is_file():
                        update_packages.append(qup_file)
                        logger.info(f"Found update package: {qup_file}")
            
            except Exception as e:
                logger.debug(f"Error scanning {mountpoint}: {e}")
        
        logger.info(f"Found {len(update_packages)} update package(s)")
        return update_packages


# Global update service instance
update_service = UpdateService()
