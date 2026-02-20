"""
Update Command
SOUP (Secure Offline Update Protocol) operations
"""
import click
from pathlib import Path

from services.update_service import update_service
from cli.utils import (
    print_success, print_error, print_info, print_header,
    print_table, print_warning, confirm_action
)
from config.logging_config import get_logger

logger = get_logger(__name__)


@click.group()
def update():
    """Manage secure offline updates (SOUP)"""
    pass


@update.command()
@click.argument('package_path', type=click.Path(exists=True))
def verify(package_path):
    """Verify an update package"""
    try:
        print_header("Verifying Update Package")
        
        package_path = Path(package_path)
        print_info(f"Package: {package_path}")
        
        # Verify
        with click.progressbar(length=100, label='Verifying') as bar:
            result = update_service.verify_update(package_path)
            bar.update(100)
        
        # Display result
        click.echo()
        
        if result['valid']:
            print_success("Package verification PASSED")
            print_info(f"Version: {result.get('version', 'unknown')}")
            print_info(f"Type: {result.get('type', 'unknown')}")
            
            if result.get('metadata'):
                click.echo("\nMetadata:")
                for key, value in result['metadata'].items():
                    click.echo(f"  {key}: {value}")
        else:
            print_error("Package verification FAILED")
            print_error(f"Reason: {result['message']}")
            click.echo("\n[WARN] DO NOT APPLY THIS UPDATE")
    
    except Exception as e:
        print_error(f"Verification failed: {e}")
        logger.error(f"Verification error: {e}", exc_info=True)
        raise click.Abort()


@update.command()
@click.argument('package_path', type=click.Path(exists=True))
@click.option('--force', is_flag=True, help='Skip confirmation')
def apply(package_path, force):
    """Apply an update package"""
    try:
        print_header("Applying Update Package")
        
        package_path = Path(package_path)
        print_info(f"Package: {package_path}")
        
        # Verify first
        print_info("Verifying package...")
        verification = update_service.verify_update(package_path)
        
        if not verification['valid']:
            print_error(f"Verification failed: {verification['message']}")
            print_error("Cannot apply invalid package")
            return
        
        print_success("Verification passed")
        print_info(f"Type: {verification.get('type')}")
        print_info(f"Version: {verification.get('version')}")
        
        # Confirm
        if not force:
            if not confirm_action("\nApply this update?"):
                print_info("Cancelled")
                return
        
        # Apply
        with click.progressbar(length=100, label='Applying update') as bar:
            result = update_service.apply_update(package_path)
            bar.update(100)
        
        click.echo()
        
        if result.get('success'):
            print_success("Update applied successfully!")
            print_info(f"Type: {result['type']}")
            print_info(f"Version: {result['version']}")
            print_warning("\nNote: Restart may be required for changes to take effect")
        else:
            print_error("Update application failed")
    
    except Exception as e:
        print_error(f"Update failed: {e}")
        logger.error(f"Update error: {e}", exc_info=True)
        raise click.Abort()


@update.command()
@click.argument('update_type', 
                type=click.Choice(['model', 'rules', 'mitre'], case_sensitive=False))
@click.confirmation_option(prompt='Are you sure you want to rollback?')
def rollback(update_type):
    """Rollback to previous version"""
    try:
        print_header(f"Rolling Back {update_type.title()} Update")
        
        with click.progressbar(length=100, label='Rolling back') as bar:
            result = update_service.rollback_update(update_type)
            bar.update(100)
        
        click.echo()
        
        if result.get('success'):
            print_success("Rollback successful!")
            print_info(result.get('message', ''))
        else:
            print_error("Rollback failed")
            print_error(result.get('message', 'Unknown error'))
    
    except Exception as e:
        print_error(f"Rollback failed: {e}")
        logger.error(f"Rollback error: {e}", exc_info=True)
        raise click.Abort()


@update.command()
def history():
    """Show update history"""
    try:
        print_header("Update History")
        
        history = update_service.get_update_history()
        
        if history:
            table_data = []
            for item in history:
                table_data.append({
                    'Timestamp': item['timestamp'][:19],
                    'Type': item['type'],
                    'Version': item.get('version', 'N/A'),
                    'Hash': item['hash'][:16] + '...'
                })
            
            print_table(table_data)
            print_info(f"\nTotal updates: {len(history)}")
        else:
            print_info("No update history")
    
    except Exception as e:
        print_error(f"Failed to get history: {e}")
        logger.error(f"History error: {e}", exc_info=True)
        raise click.Abort()


@update.command()
def scan():
    """Scan for update packages on connected devices"""
    try:
        print_header("Scanning for Update Packages")
        
        print_info("Scanning connected USB devices and storage...")
        
        with click.progressbar(length=100, label='Scanning') as bar:
            packages = update_service.scan_for_updates()
            bar.update(100)
        
        click.echo()
        
        if packages:
            print_success(f"Found {len(packages)} update package(s)!")
            
            for i, package in enumerate(packages, 1):
                click.echo(f"\n{i}. {package}")
                
                # Quick verify
                verification = update_service.verify_update(package)
                if verification['valid']:
                    click.echo(f"   [OK] Valid - {verification.get('type')} v{verification.get('version')}")
                else:
                    click.echo(f"   [ERROR] Invalid - {verification['message']}")
        else:
            print_info("No update packages found")
            print_info("Connect a USB drive with .qup files and try again")
    
    except Exception as e:
        print_error(f"Scan failed: {e}")
        logger.error(f"Scan error: {e}", exc_info=True)
        raise click.Abort()
