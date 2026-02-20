"""
Generate RSA Key Pair for SOUP
"""
from pathlib import Path
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import CryptoUtils
from config.settings import settings


def main():
    """Generate and save RSA key pair"""
    print("Generating RSA-2048 key pair for SOUP...")
    
    private_key, public_key = CryptoUtils.generate_key_pair(key_size=2048)
    
    # Save public key
    public_key_path = settings.KEYS_DIR / "public_key.pem"
    with open(public_key_path, 'wb') as f:
        f.write(public_key)
    
    print(f"✓ Public key saved: {public_key_path}")
    
    # Save private key
    private_key_path = settings.KEYS_DIR / "private_key.pem"
    with open(private_key_path, 'wb') as f:
        f.write(private_key)
    
    print(f"✓ Private key saved: {private_key_path}")
    print("\n⚠ IMPORTANT: Keep private key secure! It's used to sign updates.")


if __name__ == '__main__':
    main()