"""
Report Command - UPGRADED
Session-folder-aware report listing + multi-graph generation
"""
import click
from pathlib import Path

from services.report_service import report_service
from cli.utils import (
    print_success, print_error, print_info, print_header,
    print_table, print_warning, format_size
)
from config.logging_config import get_logger

logger = get_logger(__name__)


@click.group()
def report():
    """Generate and manage reports"""
    pass


@report.command()
@click.option('--type', '-t', 'report_type',
              type=click.Choice(['csv', 'pdf', 'both'], case_sensitive=False),
              default='both', help='Report format (default: both)')
@click.option('--session', '-s', help='Analysis session ID')
@click.option('--output', '-o', help='Custom output path')
@click.option('--no-graphs', is_flag=True, help='Skip graphs in PDF')
def generate(report_type, session, output, no_graphs):
    """
    Generate reports.

    By default generates both CSV and PDF into a session subfolder.

    Examples:\n
      quorum report generate --session <id>\n
      quorum report generate --type pdf --session <id>\n
      quorum report generate --type csv\n
    """
    try:
        print_header("Generating Report")

        if session:
            print_info(f"Session: {session}")
        else:
            print_info("Scope: All data")

        include_graphs = not no_graphs
        paths = {}

        with click.progressbar(length=100, label='Generating') as bar:
            if report_type in ('csv', 'both'):
                paths['csv'] = report_service.generate_csv_report(
                    session_id=session,
                    output_path=Path(output) if output and report_type == 'csv' else None
                )
                bar.update(40 if report_type == 'both' else 100)

            if report_type in ('pdf', 'both'):
                paths['pdf'] = report_service.generate_pdf_report(
                    session_id=session,
                    output_path=Path(output) if output and report_type == 'pdf' else None,
                    include_graphs=include_graphs
                )
                bar.update(60 if report_type == 'both' else 100)

        click.echo()
        print_success("Report(s) generated successfully!")

        for fmt, path in paths.items():
            path = Path(path)
            print_info(f"{fmt.upper()}: {path}")
            print_info(f"  Size: {format_size(path.stat().st_size)}")

        if session:
            from config.settings import settings
            session_dir = settings.REPORTS_DIR / session
            print_info(f"\nAll reports in: {session_dir}")

    except Exception as e:
        print_error(f"Report generation failed: {e}")
        logger.error(f"Report error: {e}", exc_info=True)
        raise click.Abort()


@report.command('list')
@click.option('--session', '-s', help='Filter by session ID')
def list_reports(session):
    """List all generated reports including session subfolders"""
    try:
        print_header("Generated Reports")

        all_reports = report_service.list_reports()

        if session:
            all_reports = [r for r in all_reports if session[:8] in r.get('Session', '')]

        if all_reports:
            print_table(all_reports)
            print_info(f"\nTotal: {len(all_reports)} report(s)")

            from config.settings import settings
            print_info(f"Location: {settings.REPORTS_DIR}")
        else:
            print_info("No reports found")
            print_info("Run: python main.py report generate")

    except Exception as e:
        print_error(f"Failed to list reports: {e}")
        raise click.Abort()


@report.command()
@click.argument('session_id')
def session(session_id):
    """Show all reports for a specific session"""
    try:
        from config.settings import settings

        print_header(f"Session Reports")
        print_info(f"Session: {session_id}")

        session_dir = settings.REPORTS_DIR / session_id

        if not session_dir.exists():
            print_warning("No reports found for this session")
            print_info("Generate with: python main.py report generate --session " + session_id)
            return

        files = list(session_dir.iterdir())
        if not files:
            print_warning("Session directory is empty")
            return

        table_data = []
        for f in sorted(files):
            if f.is_file():
                table_data.append({
                    'Filename': f.name,
                    'Size': format_size(f.stat().st_size),
                    'Type': f.suffix.upper()[1:]
                })

        print_table(table_data)
        print_info(f"\nLocation: {session_dir}")

    except Exception as e:
        print_error(f"Failed: {e}")
        raise click.Abort()


@report.command()
@click.argument('filepath', type=click.Path(exists=True))
def open(filepath):
    """Open a generated report file"""
    try:
        import subprocess
        import platform as plt

        path = Path(filepath)
        system = plt.system()

        if system == 'Darwin':
            subprocess.run(['open', str(path)])
        elif system == 'Windows':
            subprocess.run(['start', '', str(path)], shell=True)
        else:
            subprocess.run(['xdg-open', str(path)])

        print_success(f"Opened: {path.name}")

    except Exception as e:
        print_error(f"Failed to open: {e}")
        raise click.Abort()


@report.command()
@click.argument('filename')
@click.confirmation_option(prompt='Delete this report?')
def delete(filename):
    """Delete a report file"""
    try:
        from config.settings import settings

        # Search in reports dir and session subdirs
        found = None
        for item in settings.REPORTS_DIR.rglob(filename):
            found = item
            break

        if not found:
            print_error(f"Not found: {filename}")
            return

        found.unlink()
        print_success(f"Deleted: {filename}")

    except Exception as e:
        print_error(f"Failed to delete: {e}")
        raise click.Abort()