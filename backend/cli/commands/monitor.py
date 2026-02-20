"""
CLI Monitor Command - Real-time log tail with live anomaly scoring
"""
import click
import time
from pathlib import Path
from cli.utils import print_header, print_info, print_success, print_error, print_warning
from config.logging_config import get_logger
logger = get_logger(__name__)


@click.group()
def monitor():
    """Real-time log monitoring (tail -f with AI scoring)"""
    pass


@monitor.command()
@click.argument('files', nargs=-1, required=False)
@click.option('--auto', '-a', is_flag=True,
              help='Auto-discover and watch system log files')
@click.option('--threshold', '-t', type=float, default=0.55,
              help='Minimum score to highlight (default: 0.55)')
@click.option('--severity', '-s',
              type=click.Choice(['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'],
                                case_sensitive=False),
              default='LOW', help='Minimum severity to show')
@click.option('--no-color', is_flag=True, help='Disable colour output')
def watch(files, auto, threshold, severity, no_color):
    """
    Watch log files in real-time with live AI anomaly scoring.

    Examples:\n
      quorum monitor watch /var/log/auth.log\n
      quorum monitor watch --auto\n
      quorum monitor watch C:\\logs\\Security.log --threshold 0.70\n
    """
    from core.realtime_monitor import realtime_monitor, StreamEvent
    from services.log_service import LINUX_LOG_SOURCES, WINDOWS_LOG_SOURCES
    import platform

    SEV_ORDER = {'INFO': 0, 'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 4}
    SEV_COLORS = {
        'CRITICAL': 'red', 'HIGH': 'yellow',
        'MEDIUM': 'cyan', 'LOW': 'green', 'INFO': 'white'
    }
    min_sev = SEV_ORDER.get(severity.upper(), 1)

    print_header("Quorum Real-Time Monitor")

    # Collect files to watch
    watch_files = list(files)

    if auto:
        sources = WINDOWS_LOG_SOURCES if platform.system() == 'Windows' else LINUX_LOG_SOURCES
        for name, path in sources.items():
            p = Path(path)
            if p.exists():
                watch_files.append(str(p))
                print_info(f"Auto-added: {p.name}")

    if not watch_files:
        print_error("No files specified. Use file paths or --auto flag.")
        return

    # Register files
    added = 0
    for f in watch_files:
        if realtime_monitor.add_file(f):
            added += 1

    if added == 0:
        print_error("Could not open any log files (check permissions)")
        return

    print_success(f"Watching {added} file(s). Press Ctrl+C to stop.\n")
    print_info(f"Showing severity >= {severity}  |  score >= {threshold}\n")

    # Column header
    click.echo(
        click.style(f"{'TIME':<10} {'SEV':<10} {'SCORE':<7} {'SOURCE':<18} MESSAGE", bold=True)
    )
    click.echo("─" * 80)

    # Start monitor
    realtime_monitor.start()

    try:
        while True:
            entry = realtime_monitor.get_event(timeout=0.5)
            if not entry:
                continue

            # Filter by severity
            entry_sev = entry.severity.upper()
            if SEV_ORDER.get(entry_sev, 0) < min_sev:
                continue
            if entry.anomaly_score < threshold:
                continue

            ts      = entry.received_at.strftime("%H:%M:%S")
            source  = (entry.parsed.get('source') or Path(entry.file_path).name)[:17]
            message = (entry.parsed.get('message') or entry.raw_line)[:60]
            score   = f"{entry.anomaly_score:.3f}"

            if no_color:
                click.echo(f"{ts:<10} {entry_sev:<10} {score:<7} {source:<18} {message}")
            else:
                color = SEV_COLORS.get(entry_sev, 'white')
                line = (
                    click.style(f"{ts:<10}", fg='white') +
                    click.style(f"{entry_sev:<10}", fg=color, bold=(entry_sev == 'CRITICAL')) +
                    click.style(f"{score:<7}", fg=color) +
                    f"{source:<18} " +
                    click.style(message, fg=color if entry_sev in ('CRITICAL','HIGH') else 'white')
                )
                click.echo(line)

    except KeyboardInterrupt:
        pass
    finally:
        realtime_monitor.stop()
        stats = realtime_monitor.get_stats()
        click.echo()
        print_info(f"Lines processed: {stats['lines_processed']:,}")
        print_info(f"Anomalies found: {stats['anomalies_found']:,}")


@monitor.command()
def status():
    """Show real-time monitor status"""
    from core.realtime_monitor import realtime_monitor
    print_header("Monitor Status")
    stats = realtime_monitor.get_stats()
    print_info(f"Running:          {'Yes' if realtime_monitor.is_running() else 'No'}")
    print_info(f"Files watched:    {stats['files_watched']}")
    print_info(f"Lines processed:  {stats['lines_processed']:,}")
    print_info(f"Anomalies found:  {stats['anomalies_found']:,}")
    if stats.get('files'):
        click.echo("\nWatched files:")
        for f in stats['files']:
            click.echo(f"  • {f}")