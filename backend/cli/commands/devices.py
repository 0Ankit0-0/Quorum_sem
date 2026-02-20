"""
Devices CLI Command
Scan, list, and monitor all physical/network devices attached to this system.
Covers: USB drives, headphones, keyboards, smartphones, LAN nodes.
"""
import click
from cli.utils import (print_header, print_info, print_success,
                        print_error, print_warning, print_table)
from config.logging_config import get_logger

logger = get_logger(__name__)

RISK_COLORS = {
    'CRITICAL': 'red',
    'HIGH':     'yellow',
    'MEDIUM':   'cyan',
    'LOW':      'green',
    'INFO':     'white',
}


@click.group()
def devices():
    """Scan and monitor attached devices (USB, LAN, removable media)"""
    pass


@devices.command()
@click.option('--no-lan', is_flag=True, help='Skip LAN node discovery')
@click.option('--usb-only', is_flag=True, help='Only scan USB/physical devices')
@click.option('--json', 'as_json', is_flag=True, help='Output as JSON')
def scan(no_lan, usb_only, as_json):
    """
    Full device scan: USB devices + LAN nodes.

    Detects and classifies:\n
      • USB storage (pendrives, SD cards)\n
      • Audio devices (headphones, speakers, mics)\n
      • HID devices (keyboards, mice)\n
      • Network adapters (USB Ethernet/WiFi)\n
      • Smartphones (Android MTP, iPhone)\n
      • LAN-connected machines\n

    Examples:\n
      quorum devices scan\n
      quorum devices scan --usb-only\n
      quorum devices scan --no-lan\n
    """
    try:
        from core.device_monitor import device_monitor

        print_header("Device Scan")
        include_lan = not (no_lan or usb_only)

        with click.progressbar(length=3, label='Scanning') as bar:
            # USB
            usb_devices = device_monitor.enumerate_usb_devices()
            bar.update(1)

            # LAN
            lan_nodes = device_monitor.discover_lan_nodes() if include_lan else []
            bar.update(2)

            bar.update(1)

        click.echo()

        if as_json:
            import json
            all_devices = [d.to_dict() for d in usb_devices + lan_nodes]
            click.echo(json.dumps(all_devices, indent=2, default=str))
            return

        # ── USB Devices ─────────────────────────────────────────────────────
        if usb_devices:
            click.echo(click.style(f"\n  USB / Physical Devices ({len(usb_devices)} found)", bold=True))
            click.echo("  " + "─" * 70)

            for d in usb_devices:
                risk_color = RISK_COLORS.get(d.risk_level, 'white')
                new_badge  = click.style(' [NEW]', fg='magenta', bold=True) if d.is_new else ''
                risk_badge = click.style(f' [{d.risk_level}]', fg=risk_color, bold=True)

                click.echo(
                    f"  {click.style(d.device_class.value.upper()[:10], fg=risk_color, bold=True):<14}"
                    f"  {d.name[:35]:<37}"
                    f"{risk_badge}{new_badge}"
                )
                if d.vendor:
                    click.echo(f"  {'':14}  Vendor:  {d.vendor}")
                if d.vendor_id and d.product_id:
                    click.echo(f"  {'':14}  VID:PID: {d.vendor_id}:{d.product_id}")
                if d.serial:
                    click.echo(f"  {'':14}  Serial:  {d.serial}")
                if d.mount_point:
                    click.echo(f"  {'':14}  Mounted: {d.mount_point}")
                click.echo()
        else:
            print_info("No USB devices detected")

        # ── LAN Nodes ───────────────────────────────────────────────────────
        if include_lan:
            if lan_nodes:
                click.echo(click.style(f"\n  LAN Nodes ({len(lan_nodes)} found)", bold=True))
                click.echo("  " + "─" * 70)
                lan_table = []
                for d in lan_nodes:
                    lan_table.append({
                        'IP Address': d.ip_address or 'N/A',
                        'Hostname':   (d.name or 'Unknown')[:30],
                        'MAC':        d.mac_address or 'N/A',
                        'Status':     'NEW' if d.is_new else 'known',
                    })
                print_table(lan_table)
            else:
                print_info("No LAN nodes discovered")

        # ── Summary ─────────────────────────────────────────────────────────
        all_devices = usb_devices + lan_nodes
        risky = [d for d in all_devices if d.risk_level in ('HIGH', 'CRITICAL')]
        new   = [d for d in all_devices if d.is_new]

        click.echo()
        print_success(f"Scan complete — {len(all_devices)} device(s) found")

        if risky:
            print_warning(f"⚠  {len(risky)} high-risk device(s) detected:")
            for d in risky:
                click.echo(click.style(
                    f"   [{d.risk_level}] {d.device_class.value} — {d.name}",
                    fg=RISK_COLORS.get(d.risk_level, 'yellow')
                ))

        if new:
            click.echo(click.style(
                f"\n  ★  {len(new)} new device(s) not seen before",
                fg='magenta', bold=True
            ))

        # Offer to ingest logs from storage devices
        storage = [d for d in usb_devices if d.mount_point]
        if storage:
            click.echo()
            print_info(f"Storage devices with mount points found ({len(storage)}):")
            for d in storage:
                click.echo(f"  • {d.name} → {d.mount_point}")
            if click.confirm("\nScan storage devices for log files?", default=False):
                ctx = click.get_current_context()
                ctx.invoke(scan_logs, mount_points=[d.mount_point for d in storage])

    except Exception as e:
        print_error(f"Device scan failed: {e}")
        logger.error(f"Device scan error: {e}", exc_info=True)
        raise click.Abort()


@devices.command()
@click.option('--interval', '-i', type=int, default=5,
              help='Poll interval in seconds (default: 5)')
@click.option('--alert-only', is_flag=True,
              help='Only print alerts for new/risky devices')
def watch(interval, alert_only):
    """
    Monitor for device hotplug events in real-time.
    Alerts when USB drives, phones, or unknown devices connect/disconnect.

    Examples:\n
      quorum devices watch\n
      quorum devices watch --alert-only\n
      quorum devices watch --interval 3\n
    """
    from core.device_monitor import device_monitor
    from models.node import DeviceClass

    print_header("Device Hotplug Monitor")
    print_info(f"Polling every {interval}s. Press Ctrl+C to stop.\n")

    click.echo(click.style(f"{'TIME':<10} {'EVENT':<14} {'CLASS':<12} {'NAME':<30} RISK", bold=True))
    click.echo("─" * 80)

    def on_event(device, event):
        from datetime import datetime
        ts    = datetime.now().strftime("%H:%M:%S")
        color = 'green' if event == 'connected' else 'red'
        risk  = device.risk_level
        rc    = RISK_COLORS.get(risk, 'white')

        if alert_only and risk not in ('HIGH', 'CRITICAL') and not device.is_new:
            return

        line = (
            click.style(f"{ts:<10}", fg='white') +
            click.style(f"{event.upper():<14}", fg=color, bold=True) +
            click.style(f"{device.device_class.value:<12}", fg=rc) +
            f"{device.name[:30]:<30} " +
            click.style(f"[{risk}]", fg=rc, bold=True)
        )
        click.echo(line)

        # Extra info for risky devices
        if risk in ('HIGH', 'CRITICAL') and event == 'connected':
            click.echo(click.style(
                f"  ⚠ VID:{device.vendor_id} PID:{device.product_id} "
                f"Serial:{device.serial or 'N/A'}",
                fg='yellow'
            ))
            # Auto-log to DB already handled in device_monitor._persist_device

    device_monitor.on_device_event(on_event)
    device_monitor.start_hotplug_monitor()

    try:
        import time
        while True:
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        device_monitor.stop_hotplug_monitor()
        click.echo()
        print_info("Device monitor stopped")


@devices.command()
def history():
    """Show device connection history from database"""
    try:
        from core.database import db
        print_header("Device Connection History")

        rows = db.fetch_all("""
            SELECT device_class, name, vendor_id, product_id,
                   mount_point, ip_address, event, risk_level,
                   connected_at
            FROM device_log
            ORDER BY connected_at DESC
            LIMIT 50
        """)

        if not rows:
            print_info("No device history found")
            print_info("Run: python main.py devices watch (to start logging)")
            return

        table = []
        for r in rows:
            table.append({
                'Time':    str(r.get('connected_at', ''))[:16],
                'Event':   r.get('event', ''),
                'Class':   r.get('device_class', ''),
                'Name':    (r.get('name') or '')[:25],
                'VID:PID': f"{r.get('vendor_id','?')}:{r.get('product_id','?')}",
                'Risk':    r.get('risk_level', 'INFO'),
            })

        print_table(table)
        print_info(f"\nShowing last {len(rows)} events")

    except Exception as e:
        print_error(f"History failed: {e}")
        raise click.Abort()


@devices.command('scan-logs')
@click.argument('mount_points', nargs=-1)
@click.option('--ingest', '-i', is_flag=True,
              help='Automatically ingest discovered log files')
def scan_logs(mount_points, ingest):
    """
    Scan storage devices for log files (.evtx, .log, .syslog).

    Examples:\n
      quorum devices scan-logs D:\\ E:\\\n
      quorum devices scan-logs /media/usb0 --ingest\n
    """
    try:
        from pathlib import Path
        from core.device_monitor import device_monitor
        from services.log_service import log_service

        print_header("Log File Discovery on Storage Devices")

        # If no mount points given, discover automatically
        if not mount_points:
            usb = device_monitor.enumerate_usb_devices()
            storage = [d for d in usb if d.mount_point]
            if not storage:
                print_info("No mounted storage devices found")
                return
            mount_points = [d.mount_point for d in storage]

        all_found = []
        for mp in mount_points:
            p = Path(mp)
            if not p.exists():
                print_warning(f"Mount point not accessible: {mp}")
                continue

            click.echo(f"\nScanning {mp}...")
            for ext in ['*.evtx', '*.log', '*.syslog', '*.txt']:
                for lf in p.rglob(ext):
                    if lf.is_file() and lf.stat().st_size > 100:
                        all_found.append(lf)
                        click.echo(f"  Found: {lf.name} ({lf.stat().st_size // 1024} KB)")

        if not all_found:
            print_info("No log files found on storage devices")
            return

        print_success(f"\nTotal: {len(all_found)} log file(s) found")

        if ingest or click.confirm(f"Ingest {len(all_found)} files into Quorum?"):
            ingested = 0
            for lf in all_found:
                try:
                    stats = log_service.ingest_file(lf)
                    click.echo(f"  ✓ {lf.name}: {stats['entries_inserted']} entries")
                    ingested += 1
                except Exception as e:
                    click.echo(f"  ✗ {lf.name}: {e}")

            print_success(f"Ingested {ingested}/{len(all_found)} files")
            print_info("Run: python main.py analyze run")

    except Exception as e:
        print_error(f"Log scan failed: {e}")
        raise click.Abort()