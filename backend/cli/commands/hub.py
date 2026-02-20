"""
Hub CLI Command - Multi-node hub aggregation management
"""
import click
from pathlib import Path
from cli.utils import (print_header, print_info, print_success,
                        print_error, print_warning, print_table)
from config.logging_config import get_logger
logger = get_logger(__name__)


@click.group()
def hub():
    """Multi-node hub aggregation (register, sync, correlate)"""
    pass


@hub.command()
@click.option('--role', type=click.Choice(['terminal', 'hub']),
              default='terminal', help='Role of this node')
def register(role):
    """Register this machine as a Quorum node"""
    try:
        from services.hub_service import hub_service
        print_header("Node Registration")
        node = hub_service.register_this_node(role=role)
        print_success(f"Node registered as {role.upper()}")
        print_info(f"Node ID:    {node.node_id}")
        print_info(f"Hostname:   {node.hostname}")
        print_info(f"IP Address: {node.ip_address or 'N/A'}")
        print_info(f"Version:    {node.quorum_version}")
    except Exception as e:
        print_error(f"Registration failed: {e}")
        raise click.Abort()


@hub.command()
@click.option('--output', '-o', default=None,
              help='Output .qsp file path (default: data/sync_<id>_<ts>.qsp)')
@click.option('--no-sign', is_flag=True, help='Skip cryptographic signing')
def export(output, no_sign):
    """Export local anomalies as a sync package for hub transfer"""
    try:
        from services.hub_service import hub_service
        print_header("Exporting Sync Package")

        output_path = Path(output) if output else None
        pkg_path = hub_service.export_sync_package(
            output_path=output_path,
            sign=not no_sign
        )

        print_success("Sync package created!")
        print_info(f"File: {pkg_path}")
        print_info(f"Size: {pkg_path.stat().st_size / 1024:.1f} KB")
        print_info(f"Signed: {'No' if no_sign else 'Yes (RSA-PSS)'}")
        print_info("\nCopy this file to a USB drive and import on the hub node.")
    except Exception as e:
        print_error(f"Export failed: {e}")
        raise click.Abort()


@hub.command('import')
@click.argument('package_path', type=click.Path(exists=True))
def import_package(package_path):
    """Import a sync package from a terminal node"""
    try:
        from services.hub_service import hub_service
        print_header("Importing Sync Package")
        print_info(f"Package: {package_path}")

        result = hub_service.import_sync_package(Path(package_path))

        print_success("Import complete!")
        print_info(f"Source node:     {result['source_node']}")
        print_info(f"Anomalies merged: {result['anomalies_merged']}")
        print_info(f"Total in package: {result['total_in_package']}")
    except Exception as e:
        print_error(f"Import failed: {e}")
        raise click.Abort()


@hub.command()
def scan_usb():
    """Scan USB drives for .qsp sync packages and auto-import"""
    try:
        from services.hub_service import hub_service
        print_header("Scanning USB for Sync Packages")

        packages = hub_service.scan_usb_for_sync_packages()

        if not packages:
            print_info("No .qsp packages found on USB drives")
            return

        print_success(f"Found {len(packages)} package(s):")
        for p in packages:
            click.echo(f"  • {p}")

        if not click.confirm("\nImport all found packages?"):
            return

        for p in packages:
            try:
                result = hub_service.import_sync_package(p)
                print_success(f"Imported {p.name}: {result['anomalies_merged']} anomalies")
            except Exception as e:
                print_error(f"Failed to import {p.name}: {e}")

    except Exception as e:
        print_error(f"Scan failed: {e}")
        raise click.Abort()


@hub.command()
def dashboard():
    """Show aggregated threat dashboard across all nodes"""
    try:
        from services.hub_service import hub_service
        print_header("Hub Aggregated Dashboard")

        data = hub_service.get_aggregated_dashboard()

        if not data:
            print_info("No aggregated data. Import sync packages first.")
            return

        print_info(f"Total Nodes:      {data['total_nodes']}")
        print_info(f"Total Anomalies:  {data['total_anomalies']}")

        # Node table
        if data.get('node_threats'):
            click.echo("\nPer-Node Threat Summary:")
            table = []
            for n in data['node_threats']:
                node_id = n['source_node']
                node_info = hub_service.get_node(node_id) or {}
                table.append({
                    'Node': (node_info.get('hostname') or node_id[:12]),
                    'Total': n['total_anomalies'],
                    'Critical': n['critical'],
                    'High': n['high'],
                    'Avg Score': f"{n['avg_score']:.3f}" if n['avg_score'] else 'N/A',
                    'Last Sync': str(n['last_sync'])[:16] if n['last_sync'] else 'N/A'
                })
            print_table(table)

        # Severity distribution
        if data.get('severity_dist'):
            click.echo("\nAggregated Severity Distribution:")
            for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
                count = data['severity_dist'].get(sev, 0)
                if count > 0:
                    bar = '█' * min(count, 30)
                    click.echo(f"  {sev:<10} {count:>4}  {bar}")

    except Exception as e:
        print_error(f"Dashboard failed: {e}")
        raise click.Abort()


@hub.command()
def correlate():
    """Find attack patterns that appear across multiple nodes"""
    try:
        from services.hub_service import hub_service
        print_header("Cross-Node Attack Correlation")

        correlations = hub_service.get_cross_node_correlations()

        if not correlations:
            print_info("No cross-node correlations found")
            print_info("Import packages from multiple nodes first")
            return

        print_warning(f"Found {len(correlations)} correlated attack pattern(s)!\n")

        for c in correlations:
            threat = c['threat_level']
            color  = 'red' if threat == 'CRITICAL' else 'yellow'
            click.echo(click.style(
                f"  [{threat}] {c['mitre_technique_id']} — {c['mitre_tactic']}",
                fg=color, bold=True
            ))
            click.echo(f"    Nodes affected:  {c['node_count']} ({c['affected_nodes']})")
            click.echo(f"    Total hits:      {c['total_hits']}")
            click.echo(f"    Avg score:       {c['avg_score']:.3f}")
            click.echo(f"    First seen:      {str(c['first_seen'])[:19]}")
            click.echo(f"    Last seen:       {str(c['last_seen'])[:19]}")
            click.echo()

    except Exception as e:
        print_error(f"Correlation failed: {e}")
        raise click.Abort()


@hub.command()
def nodes():
    """List all registered nodes"""
    try:
        from services.hub_service import hub_service
        print_header("Registered Nodes")

        node_list = hub_service.list_nodes()

        if not node_list:
            print_info("No nodes registered yet")
            print_info("Run: python main.py hub register")
            return

        table = []
        for n in node_list:
            table.append({
                'Hostname': n.get('hostname', 'Unknown'),
                'Role':     n.get('role', 'terminal'),
                'Status':   n.get('status', 'unknown'),
                'Anomalies': n.get('total_anomalies', 0),
                'IP':       n.get('ip_address', 'N/A'),
                'Last Seen': str(n.get('last_seen', ''))[:16]
            })

        print_table(table)
        print_info(f"\nTotal: {len(node_list)} node(s)")

    except Exception as e:
        print_error(f"Failed to list nodes: {e}")
        raise click.Abort()