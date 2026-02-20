"""
Ingest Command - UPGRADED
Adds: scan, collect subcommands for offline log discovery
"""
import click
from pathlib import Path

from services.log_service import log_service
from cli.utils import (
    print_success, print_error, print_info, print_header,
    print_table, print_warning, format_size
)
from config.logging_config import get_logger

logger = get_logger(__name__)


@click.group()
def ingest():
    """Ingest log files into the database"""
    pass


@ingest.command()
@click.argument('file_path', type=click.Path(exists=True))
@click.option('--type', '-t', 'source_type',
              type=click.Choice(['evtx', 'syslog', 'auto'], case_sensitive=False),
              default='auto', help='Log format type')
def file(file_path, source_type):
    """Ingest a single log file"""
    try:
        file_path = Path(file_path)
        print_header("Ingesting Log File")
        print_info(f"File: {file_path}")
        print_info(f"Size: {format_size(file_path.stat().st_size)}")
        print_info(f"Type: {source_type}")

        def progress_callback(current, total, message):
            click.echo(f"\r{message}", nl=False)

        click.echo()
        stats = log_service.ingest_file(
            file_path,
            source_type if source_type != 'auto' else None,
            progress_callback
        )
        click.echo()

        print_success("Ingestion complete!")
        print_info(f"Entries ingested: {stats['entries_inserted']:,}")
        print_info(f"Parse errors: {stats['parse_errors']:,}")
        print_info(f"Duration: {stats['duration_seconds']:.2f}s")
        print_info(f"Speed: {stats['entries_per_second']:.0f} entries/sec")

    except Exception as e:
        print_error(f"Ingestion failed: {e}")
        logger.error(f"Ingestion error: {e}", exc_info=True)
        raise click.Abort()


@ingest.command()
@click.argument('directory_path', type=click.Path(exists=True))
@click.option('--recursive', '-r', is_flag=True)
@click.option('--pattern', '-p', default='*')
def directory(directory_path, recursive, pattern):
    """Ingest all log files from a directory"""
    try:
        dir_path = Path(directory_path)
        print_header("Ingesting Directory")
        print_info(f"Directory: {dir_path}")

        if recursive:
            files = list(dir_path.rglob(pattern))
        else:
            files = list(dir_path.glob(pattern))
        files = [f for f in files if f.is_file()]

        print_info(f"Found {len(files)} file(s)")
        if not files:
            print_warning("No files found")
            return

        if not click.confirm(f"Ingest {len(files)} files?"):
            return

        results = log_service.ingest_directory(dir_path, recursive, pattern)
        successful = sum(1 for r in results if 'entries_inserted' in r)
        total = sum(r.get('entries_inserted', 0) for r in results)

        print_success("Batch ingestion complete!")
        print_info(f"Successful: {successful}/{len(results)}")
        print_info(f"Total entries: {total:,}")

    except Exception as e:
        print_error(f"Directory ingestion failed: {e}")
        raise click.Abort()


@ingest.command()
def scan():
    """
    Scan this system for available offline log sources.

    Discovers Windows EVTX logs, Linux syslog files, and USB drives.
    """
    try:
        print_header("Scanning for Available Log Sources")
        print_info("Scanning system for log files...")

        result = log_service.scan_available_logs()

        system_logs = result.get('system_logs', {})
        usb_logs = result.get('usb_logs', {})

        # Display system logs
        if system_logs:
            click.echo(f"\n{click.style('System Logs Found:', bold=True)}")
            table_data = []
            for name, info in system_logs.items():
                table_data.append({
                    'Name': name,
                    'Size (MB)': info['size_mb'],
                    'Type': info['type'].upper(),
                    'Readable': '✓' if info['readable'] else '✗',
                    'Path': info['path'][:50]
                })
            print_table(table_data)
        else:
            print_info("No system logs found (may need admin/sudo privileges)")

        # Display USB logs
        if usb_logs:
            click.echo(f"\n{click.style('USB / Removable Media Logs:', bold=True)}")
            usb_table = []
            for name, info in usb_logs.items():
                usb_table.append({
                    'Name': name,
                    'Size (MB)': info['size_mb'],
                    'Type': info['type'].upper(),
                    'Readable': '✓' if info['readable'] else '✗'
                })
            print_table(usb_table)
        else:
            print_info("No USB log files found")

        click.echo()
        print_success(f"Total sources found: {result['total_found']}")
        print_info("Use 'quorum ingest collect' to ingest discovered sources")
        print_info("Use 'quorum ingest collect --source Security,System' to pick specific ones")

    except Exception as e:
        print_error(f"Scan failed: {e}")
        logger.error(f"Scan error: {e}", exc_info=True)
        raise click.Abort()


@ingest.command()
@click.option('--source', '-s', default=None,
              help='Comma-separated source names to collect (default: all found)')
@click.option('--no-usb', is_flag=True, help='Skip USB drives')
@click.option('--types', '-t', multiple=True,
              help='Specific log types (Windows: Security,System,Application)')
def collect(source, no_usb, types):
    """
    Collect and ingest logs from this system automatically.

    Examples:\n
      quorum ingest collect                         # all available\n
      quorum ingest collect --source Security,auth  # specific sources\n
      quorum ingest collect --types Security System # Windows log types\n
    """
    try:
        print_header("Collecting System Logs")

        # If specific types passed (e.g. Windows log names)
        if types:
            print_info(f"Collecting: {', '.join(types)}")
            result = log_service.ingest_system_logs(list(types))
            print_success("Collection complete!")
            print_info(f"OS: {result['system']}")
            print_info(f"Files collected: {result['files_collected']}")
            print_info(f"Files ingested: {result['files_ingested']}")
            print_info(f"Total entries: {result.get('total_entries', 0):,}")

            if result['details']:
                click.echo("\nDetails:")
                for d in result['details']:
                    if 'entries_inserted' in d:
                        name = Path(d['file_path']).name
                        click.echo(f"  ✓ {name}: {d['entries_inserted']:,} entries")
                    elif 'error' in d:
                        name = Path(d.get('file_path', '?')).name
                        click.echo(f"  ✗ {name}: {d['error']}")
            return

        # Scan first then ingest
        print_info("Scanning for available log sources...")
        scan_result = log_service.scan_available_logs()

        system_logs = scan_result.get('system_logs', {})
        usb_logs = scan_result.get('usb_logs', {})

        if not system_logs and not usb_logs:
            print_warning("No readable log sources found")
            print_info("Tip: Run with administrator/sudo privileges for full access")
            return

        # Show what was found
        all_sources = {**system_logs}
        if not no_usb:
            all_sources.update(usb_logs)

        click.echo(f"\nFound {len(all_sources)} source(s):")
        for name, info in all_sources.items():
            status = '✓' if info['readable'] else '✗ (no access)'
            click.echo(f"  {status} {name} ({info['size_mb']} MB) [{info['type'].upper()}]")

        # Filter by --source flag
        selected_sources = None
        if source:
            selected_sources = [s.strip() for s in source.split(',')]
            print_info(f"Selected: {', '.join(selected_sources)}")

        if not click.confirm(f"\nProceed with ingestion?"):
            print_info("Cancelled")
            return

        def progress_callback(current, total, message):
            click.echo(f"\r[{current}/{total}] {message}", nl=False)

        result = log_service.ingest_from_scan(
            selected_sources=selected_sources,
            include_usb=not no_usb,
            progress_callback=progress_callback
        )

        click.echo()
        print_success("Collection complete!")
        print_info(f"Sources ingested: {result['sources_ingested']}/{result['sources_scanned']}")
        print_info(f"Total entries: {result['total_entries']:,}")

        if result['details']:
            click.echo("\nDetails:")
            for d in result['details']:
                name = d.get('source_name', '?')
                if 'entries_inserted' in d:
                    click.echo(f"  ✓ {name}: {d['entries_inserted']:,} entries")
                elif 'error' in d:
                    click.echo(f"  ✗ {name}: {d['error']}")

    except Exception as e:
        print_error(f"Collection failed: {e}")
        logger.error(f"Collect error: {e}", exc_info=True)
        raise click.Abort()


@ingest.command()
@click.option('--types', '-t', multiple=True)
def system(types):
    """Collect system logs (shortcut for 'collect --types')"""
    try:
        print_header("Collecting System Logs")
        log_types = list(types) if types else None

        if log_types:
            print_info(f"Types: {', '.join(log_types)}")
        else:
            print_info("Collecting all available system logs")

        result = log_service.ingest_system_logs(log_types)

        print_success("System log collection complete!")
        print_info(f"OS: {result['system']}")
        print_info(f"Files collected: {result['files_collected']}")
        print_info(f"Files ingested: {result['files_ingested']}")
        print_info(f"Total entries: {result.get('total_entries', 0):,}")

    except Exception as e:
        print_error(f"System log collection failed: {e}")
        raise click.Abort()


@ingest.command()
def stats():
    """Show log database statistics"""
    try:
        print_header("Log Statistics")
        s = log_service.get_log_statistics()

        print_info(f"Total Logs: {s.get('total_logs', 0):,}")

        if s.get('by_severity'):
            click.echo("\nBy Severity:")
            for sev, count in s['by_severity'].items():
                click.echo(f"  {sev}: {count:,}")

        if s.get('top_sources'):
            click.echo("\nTop Sources:")
            for src in s['top_sources'][:5]:
                click.echo(f"  {src['source']}: {src['count']:,}")

        if s.get('time_range'):
            click.echo("\nTime Range:")
            click.echo(f"  Earliest: {s['time_range']['earliest']}")
            click.echo(f"  Latest: {s['time_range']['latest']}")

    except Exception as e:
        print_error(f"Stats failed: {e}")
        raise click.Abort()