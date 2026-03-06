"""
Command Registry
Secure command dispatcher for terminal API.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

from services.analysis_service import analysis_service
from services.dataset_service import dataset_service
from services.monitoring_service import monitoring_service
from services.settings_service import settings_service
from core.device_monitor import device_monitor
from config.settings import settings


@dataclass
class CommandResult:
    output: str
    error: Optional[str] = None
    exit_code: int = 0


class CommandRegistry:
    def __init__(self):
        self._commands: Dict[str, Callable[[List[str]], CommandResult]] = {
            "help": self._help,
            "scan": self._scan,
            "analyze": self._analyze,
            "monitor": self._monitor,
            "devices": self._devices,
            "reports": self._reports,
            "status": self._status,
        }

    def list_commands(self) -> Dict[str, str]:
        return {
            "help": "Show available commands",
            "scan": "Scan devices and system signals",
            "analyze <filename>": "Run analysis against uploaded dataset",
            "monitor start|stop|status": "Control persistent monitoring service",
            "devices": "List currently detected USB devices",
            "reports [filename]": "List reports metadata",
            "status": "Show system storage and runtime status",
            "clear": "Clear terminal buffer (frontend handled)",
        }

    def execute(self, command: str) -> CommandResult:
        parts = command.strip().split()
        if not parts:
            return CommandResult(output="", error="Empty command", exit_code=1)
        name = parts[0].lower()
        args = parts[1:]
        if name == "clear":
            return CommandResult(output="")
        handler = self._commands.get(name)
        if not handler:
            return CommandResult(output="", error=f"Unknown command: {name}", exit_code=1)
        try:
            return handler(args)
        except Exception as exc:
            return CommandResult(output="", error=str(exc), exit_code=1)

    def _help(self, _: List[str]) -> CommandResult:
        lines = ["Available commands:"]
        for cmd, desc in self.list_commands().items():
            lines.append(f"  {cmd:<24} {desc}")
        return CommandResult(output="\n".join(lines))

    def _scan(self, _: List[str]) -> CommandResult:
        result = device_monitor.scan_all(include_lan=True)
        summary = result.get_summary()
        return CommandResult(
            output=(
                f"Scan complete\n"
                f"USB: {summary['usb_count']}\nLAN: {summary['lan_count']}\n"
                f"Risky: {summary['risky_devices']}\nDuration: {summary['scan_duration_s']}s"
            )
        )

    def _analyze(self, args: List[str]) -> CommandResult:
        if not args:
            return CommandResult(output="", error="Usage: analyze <filename>", exit_code=2)
        filename = args[0]
        dataset = dataset_service.get_dataset_by_filename(filename)
        if not dataset:
            return CommandResult(output="", error=f"Dataset not found for {filename}", exit_code=2)
        result = analysis_service.analyze_logs(
            algorithm="auto",
            threshold=0.65,
            log_source=filename,
        )
        return CommandResult(
            output=(
                f"Analysis completed\nSession: {result.get('session_id')}\n"
                f"Algorithm: {result.get('algorithm')}\n"
                f"Anomalies: {result.get('anomalies_detected')}\n"
                f"Duration: {result.get('duration_seconds')}s"
            )
        )

    def _monitor(self, args: List[str]) -> CommandResult:
        action = args[0].lower() if args else "status"
        if action == "start":
            status = monitoring_service.start()
            return CommandResult(output=f"Monitoring started: {status}")
        if action == "stop":
            status = monitoring_service.stop()
            return CommandResult(output=f"Monitoring stopped: {status}")
        if action == "status":
            status = monitoring_service.status()
            return CommandResult(output=f"Monitoring status: {status}")
        return CommandResult(output="", error="Usage: monitor start|stop|status", exit_code=2)

    def _devices(self, _: List[str]) -> CommandResult:
        devices = device_monitor.enumerate_usb_devices()
        if not devices:
            return CommandResult(output="No USB devices detected")
        lines = ["Connected USB devices:"]
        for device in devices:
            lines.append(
                f"  {device.name} | {device.device_class.value} | risk={device.risk_level}"
            )
        return CommandResult(output="\n".join(lines))

    def _reports(self, args: List[str]) -> CommandResult:
        if not args:
            all_sets = dataset_service.list_datasets()
            return CommandResult(output=f"Datasets with reports: {len(all_sets)}")
        filename = args[0]
        rows = dataset_service.list_reports(filename)
        if not rows:
            return CommandResult(output=f"No reports for {filename}")
        lines = [f"Reports for {filename}:"]
        for row in rows:
            lines.append(f"  {row['report_id']} | {row['created_at']} | {row['hash_sha256'][:12]}")
        return CommandResult(output="\n".join(lines))

    def _status(self, _: List[str]) -> CommandResult:
        storage = settings_service.get_storage_status()
        mon = monitoring_service.status()
        return CommandResult(
            output=(
                f"Quorum {settings.APP_VERSION}\n"
                f"Storage utilization: {storage['utilization_percent']}% ({storage['alert_level']})\n"
                f"Monitoring running: {mon['running']}\n"
                f"Last sample: {mon.get('last_sample_at')}"
            )
        )


command_registry = CommandRegistry()

