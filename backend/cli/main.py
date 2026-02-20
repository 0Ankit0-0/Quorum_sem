"""
Main CLI Entry Point — v1.1.0
Registers: ingest, analyze, query, report, update, monitor, hub, devices
"""
import click

from cli.commands.ingest   import ingest
from cli.commands.analyze  import analyze
from cli.commands.query    import query
from cli.commands.report   import report
from cli.commands.update   import update
from cli.commands.monitor  import monitor
from cli.commands.hub      import hub
from cli.commands.devices  import devices
from config.settings       import settings
from config.logging_config import setup_logging, get_logger

setup_logging(
    log_level=settings.LOG_LEVEL,
    log_format=settings.LOG_FORMAT,
    log_file=settings.LOG_FILE,
    log_dir=settings.LOGS_DIR
)
logger = get_logger(__name__)


@click.group()
@click.version_option(version=settings.APP_VERSION)
def cli():
    """
    Quorum - AI-Powered Offline Log Analysis\n
    Air-gapped forensic threat detection platform.\n
    \b
    Quick start:\n
      python main.py init\n
      python main.py ingest scan          # find available logs\n
      python main.py ingest collect       # collect system logs\n
      python main.py analyze run          # run hybrid AI analysis\n
      python main.py report generate      # generate reports\n
    """
    pass


cli.add_command(ingest)
cli.add_command(analyze)
cli.add_command(query)
cli.add_command(report)
cli.add_command(update)
cli.add_command(monitor)   # NEW v1.1.0
cli.add_command(hub)       # NEW v1.1.0
cli.add_command(devices)   # NEW v1.1.0


@cli.command()
def status():
    """Show system status and statistics"""
    try:
        from cli.utils import print_header, print_info, print_success, print_warning
        from core.database import db
        from core.environment import env_detector

        print_header("Quorum System Status")

        # App info
        click.echo(click.style(f"  Version:     ", fg='cyan') + settings.APP_VERSION)
        click.echo(click.style(f"  Database:    ", fg='cyan') + str(settings.database_path))

        # DB stats
        total_logs = db.get_table_count('logs')
        total_anomalies = db.get_table_count('anomalies')
        total_sessions = db.get_table_count('analysis_sessions')

        click.echo()
        click.echo(click.style("  Database:", bold=True))
        click.echo(f"    Logs:       {total_logs:,}")
        click.echo(f"    Anomalies:  {total_anomalies:,}")
        click.echo(f"    Sessions:   {total_sessions:,}")

        # Recent session
        if total_sessions > 0:
            last = db.fetch_one(
                "SELECT session_id, start_time, anomalies_detected "
                "FROM analysis_sessions ORDER BY start_time DESC LIMIT 1"
            )
            if last:
                click.echo(f"\n  Last Analysis: {str(last['start_time'])[:16]}")
                click.echo(f"  Anomalies:     {last['anomalies_detected']}")

        # Environment
        click.echo()
        env_info = env_detector.detect_all()
        env_type = env_info.get('environment_type')
        env_val = env_type.value if env_type else 'unknown'

        env_color = {'air_gapped': 'green', 'lan_connected': 'yellow',
                     'internet_connected': 'red'}.get(env_val, 'white')

        click.echo(click.style("  Environment:", bold=True))
        click.echo(f"    Status:  " + click.style(env_val, fg=env_color))
        click.echo(f"    Role:    {env_info.get('system_role', {}).value if env_info.get('system_role') else 'unknown'}")
        click.echo(f"    OS:      {env_info.get('os', 'unknown')}")

        usb = env_info.get('usb_devices', [])
        if usb:
            click.echo(f"    USB:     {len(usb)} device(s) connected")

        # Reports
        from config.settings import settings as s
        if s.REPORTS_DIR.exists():
            session_dirs = [d for d in s.REPORTS_DIR.iterdir() if d.is_dir()]
            all_reports = list(s.REPORTS_DIR.rglob('*.pdf')) + list(s.REPORTS_DIR.rglob('*.csv'))
            if all_reports:
                click.echo(f"\n  Reports:     {len(all_reports)} file(s) in {len(session_dirs)} session(s)")

        click.echo()
        print_success("System operational")

        if total_logs == 0:
            click.echo()
            print_warning("No logs ingested yet. Try:")
            click.echo("  python main.py ingest scan")
            click.echo("  python main.py ingest file <path>")

    except Exception as e:
        from cli.utils import print_error
        print_error(f"Status check failed: {e}")
        logger.error(f"Status error: {e}", exc_info=True)


@cli.command()
def init():
    """Initialize Quorum (first-time setup)"""
    try:
        from cli.utils import print_header, print_info, print_success

        print_header("Initializing Quorum")

        print_info("Creating directories...")
        settings._create_directories()

        print_info("Initializing database...")
        from core.database import db

        print_info("Loading MITRE ATT&CK data...")
        from services.mitre_service import mitre_service
        count = db.get_table_count('mitre_techniques')
        if count == 0:
            n = mitre_service.load_mitre_data()
            print_success(f"Loaded {n} MITRE techniques")
        else:
            print_info(f"MITRE data already loaded ({count} techniques)")

        print_info("Checking cryptographic keys...")
        if not settings.public_key_path.exists():
            from core.security import CryptoUtils
            priv, pub = CryptoUtils.generate_key_pair()
            with open(settings.public_key_path, 'wb') as f:
                f.write(pub)
            priv_path = settings.KEYS_DIR / "private_key.pem"
            with open(priv_path, 'wb') as f:
                f.write(priv)
            print_success("Key pair generated")
        else:
            print_info("Keys already exist")

        print_success("\n✓ Quorum initialized successfully!")
        click.echo()
        print_info("Next steps:")
        print_info("  1. Scan for logs:    python main.py ingest scan")
        print_info("  2. Collect logs:     python main.py ingest collect")
        print_info("  3. Run analysis:     python main.py analyze run")
        print_info("  4. View results:     python main.py analyze results")
        print_info("  5. Generate report:  python main.py report generate")

    except Exception as e:
        from cli.utils import print_error
        print_error(f"Initialization failed: {e}")
        raise click.Abort()


@cli.command()
def scan():
    """Shortcut: scan system for available log files"""
    from cli.commands.ingest import scan as ingest_scan
    ctx = click.Context(ingest_scan)
    ingest_scan.invoke(ctx)


@cli.command()
def interactive():
    """Start interactive shell mode"""
    from cli.utils import print_header, print_info

    print_header("Quorum Interactive Mode")
    print_info("Commands: ingest, analyze, query, report, update, status, scan, exit")

    while True:
        try:
            raw = click.prompt("\nquorum", default="", show_default=False)
            cmd = raw.strip()

            if not cmd:
                continue
            if cmd.lower() in ['exit', 'quit', 'q']:
                print_info("Goodbye!")
                break
            if cmd.lower() == 'help':
                ctx = click.Context(cli)
                click.echo(cli.get_help(ctx))
                continue

            try:
                cli.main(cmd.split(), standalone_mode=False)
            except SystemExit:
                pass
            except Exception as e:
                from cli.utils import print_error
                print_error(str(e))

        except (KeyboardInterrupt, EOFError):
            click.echo()
            print_info("Goodbye!")
            break


if __name__ == '__main__':
    cli()