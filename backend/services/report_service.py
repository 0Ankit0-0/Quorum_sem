"""
Report Service - UPGRADED
Session-based folder structure + multiple graph types
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import csv
import json

from core.database import db
from core.exceptions import ValidationError
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger(__name__)


class ReportService:
    """Service for report generation with session-based folders and rich graphs"""

    def __init__(self):
        self.reports_dir = settings.REPORTS_DIR
        self.reports_dir.mkdir(exist_ok=True)

    def _get_session_dir(self, session_id: str) -> Path:
        """Get/create session-specific report folder"""
        session_dir = self.reports_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def generate_session_reports(self, session_id: str) -> Dict[str, Path]:
        """
        Auto-generate all reports for a session into its own folder

        Returns dict of generated file paths
        """
        logger.info(f"Auto-generating reports for session {session_id}")

        paths = {}

        try:
            paths['csv'] = self.generate_csv_report(session_id=session_id)
            paths['pdf'] = self.generate_pdf_report(session_id=session_id, include_graphs=True)
            logger.info(f"Session reports saved to {self._get_session_dir(session_id)}")
        except Exception as e:
            logger.error(f"Session report generation failed: {e}")

        return paths

    def generate_csv_report(
        self,
        session_id: Optional[str] = None,
        output_path: Optional[Path] = None
    ) -> Path:
        """Generate CSV report into session folder"""
        logger.info(f"Generating CSV report for session: {session_id or 'all'}")

        try:
            anomalies = self._query_anomalies(session_id)

            # Determine output path
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"anomaly_report_{timestamp}.csv"
                if session_id:
                    output_path = self._get_session_dir(session_id) / filename
                else:
                    output_path = self.reports_dir / filename

            output_path = Path(output_path)

            fieldnames = [
                'anomaly_id', 'threat_score', 'severity', 'algorithm',
                'timestamp', 'source', 'event_id', 'event_type',
                'hostname', 'username', 'mitre_technique', 'mitre_tactic',
                'explanation', 'message'
            ]

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for a in anomalies:
                    writer.writerow({
                        'anomaly_id': a['id'],
                        'threat_score': round(a['anomaly_score'], 4),
                        'severity': a['severity'],
                        'algorithm': a['algorithm'],
                        'timestamp': a['log_timestamp'],
                        'source': a['source'],
                        'event_id': a.get('event_id') or '',
                        'event_type': a.get('event_type') or '',
                        'hostname': a.get('hostname') or '',
                        'username': a.get('username') or '',
                        'mitre_technique': a.get('mitre_technique_id') or '',
                        'mitre_tactic': a.get('mitre_tactic') or '',
                        'explanation': a.get('explanation') or '',
                        'message': (a.get('message') or '')[:200]
                    })

            logger.info(f"CSV report: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"CSV report failed: {e}")
            raise ValidationError(f"Failed to generate CSV report: {e}")

    def generate_pdf_report(
        self,
        session_id: Optional[str] = None,
        output_path: Optional[Path] = None,
        include_graphs: bool = True
    ) -> Path:
        """Generate PDF report with multiple graphs into session folder"""
        logger.info(f"Generating PDF report for session: {session_id or 'all'}")

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph,
                Spacer, PageBreak, Image
            )
            from reportlab.lib.enums import TA_CENTER

            # Determine output path
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"threat_report_{timestamp}.pdf"
                if session_id:
                    output_path = self._get_session_dir(session_id) / filename
                else:
                    output_path = self.reports_dir / filename

            output_path = Path(output_path)

            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=1 * inch,
                bottomMargin=0.75 * inch
            )

            elements = []
            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                'Title',
                parent=styles['Heading1'],
                fontSize=22,
                textColor=colors.HexColor('#1a1a2e'),
                spaceAfter=20,
                alignment=TA_CENTER
            )
            h2_style = ParagraphStyle(
                'H2',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=colors.HexColor('#16213e'),
                spaceBefore=16,
                spaceAfter=8
            )

            elements.append(Paragraph("Quorum Threat Analysis Report", title_style))
            elements.append(Spacer(1, 0.15 * inch))

            # Metadata table
            metadata = self._get_report_metadata(session_id)
            meta_rows = [
                ['Report Generated:', metadata['generated_at']],
                ['Analysis Period:', metadata['analysis_period']],
                ['Total Logs Analyzed:', str(metadata['total_logs'])],
                ['Anomalies Detected:', str(metadata['total_anomalies'])],
            ]
            if session_id:
                meta_rows.append(['Session ID:', session_id])

            meta_table = Table(meta_rows, colWidths=[2 * inch, 4.5 * inch])
            meta_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(meta_table)
            elements.append(Spacer(1, 0.2 * inch))

            # Executive Summary
            elements.append(Paragraph("Executive Summary", h2_style))
            summary_text = self._generate_summary(metadata)
            elements.append(Paragraph(summary_text, styles['BodyText']))
            elements.append(Spacer(1, 0.1 * inch))

            if include_graphs:
                # 1. Severity bar chart
                chart1 = self._create_severity_bar_chart(session_id)
                if chart1:
                    elements.append(Paragraph("Threat Severity Distribution", h2_style))
                    elements.append(Image(chart1, width=5.5 * inch, height=2.8 * inch))
                    elements.append(Spacer(1, 0.2 * inch))

                # 2. Anomaly score timeline
                chart2 = self._create_score_timeline(session_id)
                if chart2:
                    elements.append(Paragraph("Anomaly Score Timeline", h2_style))
                    elements.append(Image(chart2, width=5.5 * inch, height=2.8 * inch))
                    elements.append(Spacer(1, 0.2 * inch))

                # 3. Top sources pie chart
                chart3 = self._create_source_pie_chart(session_id)
                if chart3:
                    elements.append(Paragraph("Anomalies by Source", h2_style))
                    elements.append(Image(chart3, width=4.5 * inch, height=3 * inch))
                    elements.append(Spacer(1, 0.2 * inch))

                # 4. MITRE tactic distribution
                chart4 = self._create_mitre_bar_chart(session_id)
                if chart4:
                    elements.append(Paragraph("MITRE ATT&CK Tactic Distribution", h2_style))
                    elements.append(Image(chart4, width=5.5 * inch, height=2.8 * inch))
                    elements.append(Spacer(1, 0.2 * inch))

            # Top anomalies table
            elements.append(PageBreak())
            elements.append(Paragraph("Top Detected Threats", h2_style))

            top_anomalies = self._get_top_anomalies(session_id, limit=15)

            if top_anomalies:
                header = ['Score', 'Severity', 'Technique', 'Source', 'Timestamp']
                rows = [header]
                for a in top_anomalies:
                    rows.append([
                        f"{a['anomaly_score']:.3f}",
                        a['severity'],
                        a.get('mitre_technique_id') or 'N/A',
                        (a['source'] or '')[:18],
                        str(a['log_timestamp'])[:16]
                    ])

                col_widths = [0.8*inch, 1*inch, 1.2*inch, 1.8*inch, 1.8*inch]
                t = Table(rows, colWidths=col_widths)

                severity_colors = {
                    'CRITICAL': colors.HexColor('#ffcccc'),
                    'HIGH': colors.HexColor('#ffe0cc'),
                    'MEDIUM': colors.HexColor('#fff3cc'),
                    'LOW': colors.HexColor('#ccffcc'),
                }

                table_style = [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                    ('TOPPADDING', (0, 0), (-1, -1), 5),
                ]

                # Color rows by severity
                for row_idx, a in enumerate(top_anomalies, 1):
                    sev = a.get('severity', '')
                    bg = severity_colors.get(sev, colors.white)
                    table_style.append(('BACKGROUND', (0, row_idx), (-1, row_idx), bg))

                t.setStyle(TableStyle(table_style))
                elements.append(t)

            # MITRE Summary
            mitre_summary = self._get_mitre_summary(session_id)
            if mitre_summary and mitre_summary.get('unique_techniques', 0) > 0:
                elements.append(Spacer(1, 0.3 * inch))
                elements.append(Paragraph("MITRE ATT&CK Coverage", h2_style))
                mitre_text = (
                    f"Detected techniques span <b>{mitre_summary['unique_tactics']}</b> tactic(s) "
                    f"and <b>{mitre_summary['unique_techniques']}</b> unique technique(s) "
                    f"from the MITRE ATT&CK framework."
                )
                elements.append(Paragraph(mitre_text, styles['BodyText']))

            doc.build(elements)
            logger.info(f"PDF report: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"PDF report failed: {e}")
            raise ValidationError(f"Failed to generate PDF: {e}")

    # ─── Graph Generators ────────────────────────────────────────────

    def _create_severity_bar_chart(self, session_id: Optional[str]) -> Optional[Path]:
        """Bar chart: severity distribution"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            data = self._query_severity_distribution(session_id)
            if not data:
                return None

            all_severities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
            counts = [data.get(s, 0) for s in all_severities]
            chart_colors = ['#388e3c', '#fbc02d', '#f57c00', '#d32f2f']

            fig, ax = plt.subplots(figsize=(7, 3.5))
            bars = ax.bar(all_severities, counts, color=chart_colors, width=0.5,
                          edgecolor='white', linewidth=1.2)

            # Add value labels
            for bar, count in zip(bars, counts):
                if count > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.1,
                            str(count), ha='center', va='bottom', fontweight='bold', fontsize=11)

            ax.set_xlabel('Severity Level', fontsize=10)
            ax.set_ylabel('Count', fontsize=10)
            ax.set_title('Anomaly Distribution by Severity', fontsize=12, fontweight='bold')
            ax.set_facecolor('#f8f9fa')
            fig.patch.set_facecolor('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            chart_path = self._chart_path(session_id, "severity_bar")
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            return chart_path

        except Exception as e:
            logger.error(f"Severity chart failed: {e}")
            return None

    def _create_score_timeline(self, session_id: Optional[str]) -> Optional[Path]:
        """Line chart: anomaly scores over time"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            from datetime import datetime as dt

            query = """
                SELECT a.anomaly_score, a.severity, l.timestamp
                FROM anomalies a
                JOIN logs l ON a.log_id = l.id
                ORDER BY l.timestamp
            """
            rows = db.fetch_all(query)
            if not rows or len(rows) < 2:
                return None

            timestamps = []
            scores = []
            sev_colors = []
            color_map = {'CRITICAL': '#d32f2f', 'HIGH': '#f57c00',
                         'MEDIUM': '#fbc02d', 'LOW': '#388e3c'}

            for r in rows:
                try:
                    ts = r['timestamp']
                    if isinstance(ts, str):
                        ts = dt.fromisoformat(ts)
                    timestamps.append(ts)
                    scores.append(r['anomaly_score'])
                    sev_colors.append(color_map.get(r['severity'], '#757575'))
                except Exception:
                    continue

            if len(timestamps) < 2:
                return None

            fig, ax = plt.subplots(figsize=(7, 3.5))
            ax.plot(timestamps, scores, color='#1565c0', linewidth=1.5,
                    alpha=0.7, zorder=1)
            ax.scatter(timestamps, scores, c=sev_colors, s=50, zorder=2,
                       edgecolors='white', linewidth=0.5)

            # Threshold line
            ax.axhline(y=0.70, color='#f57c00', linestyle='--', linewidth=1,
                       alpha=0.7, label='HIGH threshold (0.70)')
            ax.axhline(y=0.90, color='#d32f2f', linestyle='--', linewidth=1,
                       alpha=0.7, label='CRITICAL threshold (0.90)')

            ax.set_xlabel('Time', fontsize=10)
            ax.set_ylabel('Anomaly Score', fontsize=10)
            ax.set_title('Anomaly Scores Over Time', fontsize=12, fontweight='bold')
            ax.set_ylim(0, 1.05)
            ax.legend(fontsize=8)
            ax.set_facecolor('#f8f9fa')
            fig.patch.set_facecolor('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            fig.autofmt_xdate()

            chart_path = self._chart_path(session_id, "score_timeline")
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            return chart_path

        except Exception as e:
            logger.error(f"Timeline chart failed: {e}")
            return None

    def _create_source_pie_chart(self, session_id: Optional[str]) -> Optional[Path]:
        """Pie chart: anomalies by source"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            query = """
                SELECT l.source, COUNT(*) as count
                FROM anomalies a
                JOIN logs l ON a.log_id = l.id
                GROUP BY l.source
                ORDER BY count DESC
                LIMIT 8
            """
            rows = db.fetch_all(query)
            if not rows:
                return None

            labels = [r['source'] for r in rows]
            sizes = [r['count'] for r in rows]

            fig, ax = plt.subplots(figsize=(6, 4))
            wedge_props = dict(width=0.6, edgecolor='white', linewidth=2)
            ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                   startangle=90, wedgeprops=wedge_props,
                   pctdistance=0.75)

            ax.set_title('Anomalies by Source', fontsize=12, fontweight='bold')

            chart_path = self._chart_path(session_id, "source_pie")
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            return chart_path

        except Exception as e:
            logger.error(f"Pie chart failed: {e}")
            return None

    def _create_mitre_bar_chart(self, session_id: Optional[str]) -> Optional[Path]:
        """Horizontal bar chart: MITRE ATT&CK tactic distribution"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            query = """
                SELECT mitre_tactic, COUNT(*) as count
                FROM anomalies
                WHERE mitre_tactic IS NOT NULL
                GROUP BY mitre_tactic
                ORDER BY count DESC
            """
            rows = db.fetch_all(query)
            if not rows:
                return None

            tactics = [r['mitre_tactic'].replace('_', ' ').title() for r in rows]
            counts = [r['count'] for r in rows]

            fig, ax = plt.subplots(figsize=(7, max(3, len(tactics) * 0.5)))
            bars = ax.barh(tactics, counts, color='#1565c0', edgecolor='white')

            for bar, count in zip(bars, counts):
                ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2.,
                        str(count), va='center', fontsize=9, fontweight='bold')

            ax.set_xlabel('Count', fontsize=10)
            ax.set_title('MITRE ATT&CK Tactic Distribution', fontsize=12, fontweight='bold')
            ax.set_facecolor('#f8f9fa')
            fig.patch.set_facecolor('white')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            chart_path = self._chart_path(session_id, "mitre_tactics")
            plt.tight_layout()
            plt.savefig(chart_path, dpi=150, bbox_inches='tight')
            plt.close()
            return chart_path

        except Exception as e:
            logger.error(f"MITRE chart failed: {e}")
            return None

    def _chart_path(self, session_id: Optional[str], name: str) -> Path:
        """Get chart file path inside session folder or reports dir"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{ts}.png"
        if session_id:
            return self._get_session_dir(session_id) / filename
        return self.reports_dir / filename

    # ─── Data Helpers ────────────────────────────────────────────────

    def _query_anomalies(self, session_id: Optional[str]) -> List[Dict[str, Any]]:
        if session_id:
            query = """
                SELECT a.id, a.anomaly_score, a.algorithm, a.severity,
                       a.explanation, a.mitre_technique_id, a.mitre_tactic, a.detected_at,
                       l.timestamp as log_timestamp, l.source, l.event_id, l.event_type,
                       l.hostname, l.username, l.message
                FROM anomalies a
                JOIN logs l ON a.log_id = l.id
                WHERE a.detected_at >= (
                    SELECT start_time FROM analysis_sessions WHERE session_id = ?
                )
                ORDER BY a.anomaly_score DESC
            """
            return db.fetch_all(query, (session_id,))
        else:
            query = """
                SELECT a.id, a.anomaly_score, a.algorithm, a.severity,
                       a.explanation, a.mitre_technique_id, a.mitre_tactic, a.detected_at,
                       l.timestamp as log_timestamp, l.source, l.event_id, l.event_type,
                       l.hostname, l.username, l.message
                FROM anomalies a
                JOIN logs l ON a.log_id = l.id
                ORDER BY a.anomaly_score DESC
            """
            return db.fetch_all(query)

    def _query_severity_distribution(self, session_id: Optional[str]) -> Dict[str, int]:
        if session_id:
            query = """
                SELECT severity, COUNT(*) as count
                FROM anomalies
                WHERE detected_at >= (
                    SELECT start_time FROM analysis_sessions WHERE session_id = ?
                )
                GROUP BY severity
            """
            rows = db.fetch_all(query, (session_id,))
        else:
            query = "SELECT severity, COUNT(*) as count FROM anomalies GROUP BY severity"
            rows = db.fetch_all(query)

        return {r['severity']: r['count'] for r in rows}

    def _get_report_metadata(self, session_id: Optional[str]) -> Dict[str, Any]:
        metadata = {
            'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'total_logs': 0,
            'total_anomalies': 0,
            'analysis_period': 'All time'
        }
        try:
            metadata['total_logs'] = db.get_table_count('logs')
            if session_id:
                r = db.fetch_one(
                    "SELECT COUNT(*) as count FROM anomalies WHERE detected_at >= "
                    "(SELECT start_time FROM analysis_sessions WHERE session_id = ?)",
                    (session_id,)
                )
                metadata['total_anomalies'] = r['count'] if r else 0
                sess = db.fetch_one(
                    "SELECT start_time, end_time FROM analysis_sessions WHERE session_id = ?",
                    (session_id,)
                )
                if sess:
                    metadata['analysis_period'] = (
                        f"{sess['start_time']} to {sess['end_time'] or 'Present'}"
                    )
            else:
                metadata['total_anomalies'] = db.get_table_count('anomalies')
        except Exception as e:
            logger.error(f"Metadata error: {e}")
        return metadata

    def _generate_summary(self, metadata: Dict[str, Any]) -> str:
        total_logs = metadata['total_logs']
        total_anomalies = metadata['total_anomalies']
        if total_logs == 0:
            return "No log data available."
        rate = (total_anomalies / total_logs) * 100
        return (
            f"This report presents results of automated threat detection on {total_logs:,} log entries. "
            f"The hybrid AI engine identified {total_anomalies:,} anomalies ({rate:.2f}% anomaly rate). "
            f"Anomalies are ranked by threat score and mapped to MITRE ATT&CK techniques where applicable."
        )

    def _get_top_anomalies(self, session_id: Optional[str], limit: int = 15) -> List[Dict[str, Any]]:
        try:
            if session_id:
                query = """
                    SELECT a.anomaly_score, a.severity, a.mitre_technique_id,
                           l.timestamp as log_timestamp, l.source
                    FROM anomalies a JOIN logs l ON a.log_id = l.id
                    WHERE a.detected_at >= (
                        SELECT start_time FROM analysis_sessions WHERE session_id = ?
                    )
                    ORDER BY a.anomaly_score DESC LIMIT ?
                """
                return db.fetch_all(query, (session_id, limit))
            else:
                query = """
                    SELECT a.anomaly_score, a.severity, a.mitre_technique_id,
                           l.timestamp as log_timestamp, l.source
                    FROM anomalies a JOIN logs l ON a.log_id = l.id
                    ORDER BY a.anomaly_score DESC LIMIT ?
                """
                return db.fetch_all(query, (limit,))
        except Exception as e:
            logger.error(f"Top anomalies error: {e}")
            return []

    def _get_mitre_summary(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        try:
            if session_id:
                return db.fetch_one("""
                    SELECT COUNT(DISTINCT mitre_technique_id) as unique_techniques,
                           COUNT(DISTINCT mitre_tactic) as unique_tactics
                    FROM anomalies
                    WHERE mitre_technique_id IS NOT NULL
                    AND detected_at >= (
                        SELECT start_time FROM analysis_sessions WHERE session_id = ?
                    )
                """, (session_id,))
            else:
                return db.fetch_one("""
                    SELECT COUNT(DISTINCT mitre_technique_id) as unique_techniques,
                           COUNT(DISTINCT mitre_tactic) as unique_tactics
                    FROM anomalies WHERE mitre_technique_id IS NOT NULL
                """)
        except Exception as e:
            logger.error(f"MITRE summary error: {e}")
            return None

    def list_reports(self) -> List[Dict[str, Any]]:
        """List all reports including session subfolders"""
        reports = []
        try:
            for item in self.reports_dir.iterdir():
                if item.is_dir():
                    # Session folder
                    for f in item.iterdir():
                        if f.is_file():
                            reports.append({
                                'Filename': f.name,
                                'Session': item.name[:8] + '...',
                                'Size': f"{f.stat().st_size / 1024:.1f} KB",
                                'Created': datetime.fromtimestamp(
                                    f.stat().st_mtime
                                ).strftime("%Y-%m-%d %H:%M"),
                                'Type': f.suffix.upper()[1:],
                                'Path': str(f)
                            })
                elif item.is_file():
                    reports.append({
                        'Filename': item.name,
                        'Session': 'N/A',
                        'Size': f"{item.stat().st_size / 1024:.1f} KB",
                        'Created': datetime.fromtimestamp(
                            item.stat().st_mtime
                        ).strftime("%Y-%m-%d %H:%M"),
                        'Type': item.suffix.upper()[1:],
                        'Path': str(item)
                    })
        except Exception as e:
            logger.error(f"List reports error: {e}")

        reports.sort(key=lambda x: x['Created'], reverse=True)
        return reports


# Global instance
report_service = ReportService()