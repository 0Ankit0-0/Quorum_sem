"""
Analyze Command - UPGRADED
Default: ensemble algorithm, threshold 0.70, realistic severity output
"""
import click
from datetime import datetime

from services.analysis_service import analysis_service
from cli.utils import (
    print_success, print_error, print_info, print_header,
    print_table, print_warning
)
from config.logging_config import get_logger

logger = get_logger(__name__)


@click.group()
def analyze():
    """Run anomaly detection analysis"""
    pass


@analyze.command()
@click.option('--algorithm', '-a',
              type=click.Choice(['isolation_forest', 'one_class_svm',
                                 'statistical', 'ensemble']),
              default='ensemble',
              help='Detection algorithm (default: ensemble)')
@click.option('--threshold', '-t', type=float, default=0.70,
              help='Anomaly score threshold 0.0-1.0 (default: 0.70)')
@click.option('--contamination', '-c', type=float, default=0.05,
              help='Expected anomaly fraction 0.01-0.20 (default: 0.05)')
@click.option('--start', type=str, help='Start time (ISO format, e.g. 2026-01-01T00:00:00)')
@click.option('--end', type=str, help='End time (ISO format)')
@click.option('--no-report', is_flag=True, help='Skip auto-report generation')
def run(algorithm, threshold, contamination, start, end, no_report):
    """
    Run hybrid AI anomaly detection on ingested logs.

    The ensemble mode combines Isolation Forest + One-Class SVM + Statistical
    + Keyword analysis for realistic severity distribution.

    Examples:\n
      quorum analyze run\n
      quorum analyze run --algorithm ensemble --threshold 0.65\n
      quorum analyze run --start 2026-01-01T00:00:00\n
    """
    try:
        print_header("Running Anomaly Detection")
        print_info(f"Algorithm: {algorithm}")
        print_info(f"Threshold: {threshold}")
        print_info(f"Contamination: {contamination}")
        if start:
            print_info(f"Start: {start}")
        if end:
            print_info(f"End: {end}")

        start_time = datetime.fromisoformat(start) if start else None
        end_time = datetime.fromisoformat(end) if end else None

        def progress_callback(current, total, message):
            click.echo(f"\r{message}{'.' * (current % 4 + 1)}", nl=False)

        click.echo("\nAnalyzing logs...")

        result = analysis_service.analyze_logs(
            algorithm=algorithm,
            start_time=start_time,
            end_time=end_time,
            threshold=threshold,
            contamination=contamination,
            progress_callback=progress_callback,
            auto_report=not no_report
        )

        click.echo()
        print_success("Analysis complete!")
        print_info(f"Session ID:          {result['session_id']}")
        print_info(f"Logs analyzed:       {result['logs_analyzed']:,}")
        print_info(f"Anomalies detected:  {result['anomalies_detected']:,}")
        print_info(f"Duration:            {result['duration_seconds']:.2f}s")

        # Severity distribution
        if result.get('summary'):
            summary = result['summary']
            dist = summary.get('severity_distribution', {})

            if dist:
                click.echo("\nSeverity Distribution:")
                sev_colors = {
                    'CRITICAL': 'red', 'HIGH': 'yellow',
                    'MEDIUM': 'cyan', 'LOW': 'green'
                }
                for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                    count = dist.get(sev, 0)
                    if count > 0:
                        bar = '█' * min(count, 40)
                        colored = click.style(f"  {sev:<10} {count:>4}  {bar}",
                                              fg=sev_colors.get(sev, 'white'))
                        click.echo(colored)

            anomaly_rate = summary.get('anomaly_rate', 0)
            click.echo(f"\nAnomaly rate: {anomaly_rate:.1f}%")

        if not no_report:
            from config.settings import settings
            session_dir = settings.REPORTS_DIR / result['session_id']
            if session_dir.exists():
                print_success(f"\nReports saved to: {session_dir}")
                for f in session_dir.iterdir():
                    print_info(f"  - {f.name}")

        click.echo()
        print_info(f"View results: python main.py analyze results {result['session_id']}")

    except Exception as e:
        print_error(f"Analysis failed: {e}")
        logger.error(f"Analysis error: {e}", exc_info=True)
        raise click.Abort()


@analyze.command()
@click.argument('session_id', required=False)
@click.option('--limit', '-l', type=int, default=20)
def results(session_id, limit):
    """View analysis results"""
    try:
        if session_id:
            print_header(f"Analysis Results")
            print_info(f"Session: {session_id}")

            r = analysis_service.get_session_results(session_id)

            if 'error' in r:
                print_error(r['error'])
                return

            session = r['session']
            print_info(f"Status:     {session['status']}")
            print_info(f"Started:    {session['start_time']}")
            if session.get('end_time'):
                print_info(f"Ended:      {session['end_time']}")
            print_info(f"Logs:       {session['logs_analyzed']:,}")
            print_info(f"Anomalies:  {session['anomalies_detected']:,}")

            anomalies = r['anomalies'][:limit]
            if anomalies:
                click.echo(f"\nTop {len(anomalies)} Anomalies:")
                table_data = []
                for a in anomalies:
                    sev = a['severity']
                    score = f"{a['anomaly_score']:.3f}"
                    table_data.append({
                        'Score': score,
                        'Severity': sev,
                        'Source': (a.get('source') or '')[:20],
                        'Event': (a.get('event_type') or 'N/A')[:18],
                        'MITRE': a.get('mitre_technique_id') or 'N/A',
                        'Timestamp': str(a.get('timestamp', ''))[:16]
                    })
                print_table(table_data)

        else:
            print_header("Recent Analysis Sessions")
            from core.database import db

            sessions = db.fetch_all("""
                SELECT session_id, start_time, status,
                       logs_analyzed, anomalies_detected
                FROM analysis_sessions
                ORDER BY start_time DESC
                LIMIT ?
            """, (limit,))

            if sessions:
                print_table(sessions)
            else:
                print_info("No sessions found. Run: python main.py analyze run")

    except Exception as e:
        print_error(f"Failed to get results: {e}")
        raise click.Abort()


@analyze.command()
@click.option('--severity', '-s',
              type=click.Choice(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'],
                                case_sensitive=False))
@click.option('--limit', '-l', type=int, default=50)
def anomalies(severity, limit):
    """List detected anomalies with severity filter"""
    try:
        print_header("Detected Anomalies")

        from core.database import db
        conditions, params = [], []

        if severity:
            conditions.append("a.severity = ?")
            params.append(severity.upper())

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = db.fetch_all(f"""
            SELECT a.anomaly_score, a.severity, a.mitre_technique_id,
                   a.explanation, l.timestamp, l.source, l.event_type
            FROM anomalies a
            JOIN logs l ON a.log_id = l.id
            WHERE {where}
            ORDER BY a.anomaly_score DESC
            LIMIT ?
        """, tuple(params))

        if rows:
            table_data = [{
                'Score': f"{r['anomaly_score']:.3f}",
                'Severity': r['severity'],
                'Source': (r['source'] or '')[:20],
                'Event': (r.get('event_type') or 'N/A')[:18],
                'MITRE': r.get('mitre_technique_id') or 'N/A',
                'Timestamp': str(r['timestamp'])[:16]
            } for r in rows]
            print_table(table_data)

            # Severity summary
            click.echo()
            from collections import Counter
            counts = Counter(r['severity'] for r in rows)
            for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                if counts.get(sev, 0) > 0:
                    click.echo(f"  {sev}: {counts[sev]}")
        else:
            print_info("No anomalies found")
            print_info("Run: python main.py analyze run")

    except Exception as e:
        print_error(f"Failed: {e}")
        raise click.Abort()