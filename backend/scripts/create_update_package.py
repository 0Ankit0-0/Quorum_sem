"""
Create Signed Update Package (SOUP)
"""
import json
import base64
import hashlib
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import CryptoUtils
from config.settings import settings


def create_update_package(
    update_type: str,
    data: dict,
    version: str,
    private_key_path: Path,
    output_path: Path
):
    """
    Create a signed update package
    
    Args:
        update_type: Type of update ('model', 'rules', 'mitre')
        data: Update data
        version: Version string
        private_key_path: Path to private key
        output_path: Output .qup file path
    """
    print(f"Creating {update_type} update package v{version}...")
    
    # Load private key
    with open(private_key_path, 'rb') as f:
        private_key = f.read()
    
    # Create payload
    payload = {
        'type': update_type,
        'version': version,
        'data': data,
        'metadata': {
            'created_at': datetime.utcnow().isoformat(),
            'description': f'{update_type.title()} update'
        }
    }
    
    # Serialize payload
    payload_str = json.dumps(payload, default=str)
    payload_bytes = payload_str.encode('utf-8')
    
    # Calculate hash
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    
    # Sign
    signature = CryptoUtils.sign_data(private_key, payload_bytes)
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    
    # Create package
    package = {
        'payload': payload_str,
        'hash': payload_hash,
        'signature': signature_b64,
        'algorithm': 'RSA-PSS',
        'hash_algorithm': 'SHA256'
    }
    
    # Save package
    with open(output_path, 'w') as f:
        json.dump(package, f, indent=2)
    
    print(f"✓ Package created: {output_path}")
    print(f"  Hash: {payload_hash}")
    print(f"  Size: {output_path.stat().st_size} bytes")


def main():
    """Example: Create a rules update package"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create update package')
    parser.add_argument('--type', required=True, choices=['model', 'rules', 'mitre'])
    parser.add_argument('--version', required=True, help='Version string')
    parser.add_argument('--output', required=True, help='Output .qup file')
    
    args = parser.parse_args()
    
    # Example data (customize based on type)
    if args.type == 'rules':
        data = {
            'rules': [
                {
                    'id': 'rule_001',
                    'name': 'Suspicious PowerShell Activity',
                    'pattern': 'powershell.*-enc.*',
                    'severity': 'HIGH'
                }
            ]
        }
    elif args.type == 'model':
        data = {
            'model_type': 'isolation_forest',
            'model_file': ''  # Base64 encoded model file
        }
    else:
        print("For MITRE updates, provide enterprise-attack.json data")
        return
    
    # Get private key
    private_key_path = settings.KEYS_DIR / "private_key.pem"
    
    if not private_key_path.exists():
        print("Error: Private key not found. Run generate_keys.py first.")
        return
    
    # Create package
    create_update_package(
        update_type=args.type,
        data=data,
        version=args.version,
        private_key_path=private_key_path,
        output_path=Path(args.output)
    )


if __name__ == '__main__':
    main()