"""
CLI Utilities
Helper functions for CLI operations
"""
import click
from typing import Any
import json
from datetime import datetime


def print_success(message: str):
    """Print success message in green"""
    click.secho(f"[OK] {message}", fg='green')


def print_error(message: str):
    """Print error message in red"""
    click.secho(f"[ERROR] {message}", fg='red', err=True)


def print_warning(message: str):
    """Print warning message in yellow"""
    click.secho(f"[WARN] {message}", fg='yellow')


def print_info(message: str):
    """Print info message"""
    click.echo(f"[INFO] {message}")


def print_header(message: str):
    """Print section header"""
    click.secho(f"\n{'=' * 60}", fg='cyan')
    click.secho(f"  {message}", fg='cyan', bold=True)
    click.secho(f"{'=' * 60}\n", fg='cyan')


def print_table(data: list, headers: list = None):
    """Print data as a formatted table"""
    if not data:
        print_info("No data to display")
        return

    # Auto-detect headers from first row if not provided
    if headers is None and isinstance(data[0], dict):
        headers = list(data[0].keys())

    if headers:
        # Calculate column widths
        col_widths = {h: len(str(h)) for h in headers}

        for row in data:
            if isinstance(row, dict):
                for header in headers:
                    value = str(row.get(header, ''))
                    col_widths[header] = max(col_widths[header], len(value))

        # Print header
        header_line = " | ".join(
            str(h).ljust(col_widths[h]) for h in headers
        )
        click.secho(header_line, bold=True)
        click.echo("-" * len(header_line))

        # Print rows
        for row in data:
            if isinstance(row, dict):
                row_line = " | ".join(
                    str(row.get(h, '')).ljust(col_widths[h]) for h in headers
                )
                click.echo(row_line)
    else:
        # Simple list printing
        for item in data:
            click.echo(f"  - {item}")


def print_json(data: Any, indent: int = 2):
    """Print data as formatted JSON"""
    click.echo(json.dumps(data, indent=indent, default=str))


def confirm_action(message: str, default: bool = False) -> bool:
    """Ask user for confirmation"""
    return click.confirm(message, default=default)


def format_timestamp(timestamp: Any) -> str:
    """Format timestamp for display"""
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp)
        except Exception:
            return str(timestamp)

    if isinstance(timestamp, datetime):
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    return str(timestamp)


def format_size(size_bytes: int) -> str:
    """Format file size for display"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


def progress_bar(iterable, length=None, label='Processing'):
    """Create a progress bar for iterations"""
    return click.progressbar(
        iterable,
        length=length,
        label=label,
        show_pos=True,
        show_percent=True
    )
