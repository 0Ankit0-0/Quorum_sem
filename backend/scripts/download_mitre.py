"""
Download MITRE ATT&CK Data
"""
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings


def main():
    """Download MITRE ATT&CK enterprise data"""
    url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
    output_path = settings.MITRE_DIR / "enterprise-attack.json"
    
    print(f"Downloading MITRE ATT&CK data from {url}...")
    
    try:
        settings.MITRE_DIR.mkdir(parents=True, exist_ok=True)
        
        urllib.request.urlretrieve(url, output_path)
        
        print(f"✓ Downloaded to {output_path}")
        print(f"  Size: {output_path.stat().st_size / 1024:.2f} KB")
    
    except Exception as e:
        print(f"✗ Download failed: {e}")


if __name__ == '__main__':
    main()