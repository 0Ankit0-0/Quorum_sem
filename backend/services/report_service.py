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
        """Generate a structured, branded PDF threat-analysis report."""
        logger.info(f"Generating PDF report for session: {session_id or 'all'}")

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.units import inch
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
            from reportlab.platypus import (
                SimpleDocTemplate, Table, TableStyle, Paragraph,
                Spacer, PageBreak, Image, HRFlowable, KeepTogether,
            )

            # ── Output path ───────────────────────────────────────────
            if not output_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"threat_report_{timestamp}.pdf"
                output_path = (
                    self._get_session_dir(session_id) if session_id
                    else self.reports_dir
                ) / filename
            output_path = Path(output_path)

            # ── Colour palette ────────────────────────────────────────
            NAVY        = colors.HexColor('#0f172a')
            NAVY_MID    = colors.HexColor('#1e293b')
            ACCENT      = colors.HexColor('#0ea5e9')
            ACCENT_LT   = colors.HexColor('#e0f2fe')
            ROW_ALT     = colors.HexColor('#f8fafc')
            GRAY_100    = colors.HexColor('#f1f5f9')
            GRAY_300    = colors.HexColor('#cbd5e1')
            GRAY_500    = colors.HexColor('#64748b')
            GRAY_700    = colors.HexColor('#334155')
            WHITE       = colors.white
            C_CRITICAL  = colors.HexColor('#fef2f2')
            C_HIGH      = colors.HexColor('#fff7ed')
            C_MEDIUM    = colors.HexColor('#fefce8')
            C_LOW       = colors.HexColor('#f0fdf4')
            T_CRITICAL  = colors.HexColor('#dc2626')
            T_HIGH      = colors.HexColor('#ea580c')
            T_MEDIUM    = colors.HexColor('#ca8a04')
            T_LOW       = colors.HexColor('#16a34a')
            PAGE_W, PAGE_H = letter

            # ── Styles ────────────────────────────────────────────────
            _ss = getSampleStyleSheet()

            def _ps(name, **kw):
                parent = _ss.get(kw.pop('parent', 'Normal'), _ss['Normal'])
                base = dict(fontName='Helvetica', fontSize=9, textColor=GRAY_700)
                base.update(kw)
                return ParagraphStyle(name, parent=parent, **base)

            cover_brand = _ps('CoverBrand', fontSize=11, fontName='Helvetica-Bold',
                               textColor=ACCENT, spaceAfter=6, alignment=TA_CENTER)
            cover_title = _ps('CoverTitle', fontSize=26, fontName='Helvetica-Bold',
                               textColor=NAVY, spaceAfter=6, alignment=TA_CENTER, leading=32)
            cover_sub   = _ps('CoverSub', fontSize=9, textColor=GRAY_500,
                               spaceAfter=3, alignment=TA_CENTER)
            caption     = _ps('Caption', fontSize=8, textColor=GRAY_500,
                               alignment=TA_CENTER, spaceAfter=2)
            body_style  = _ps('Body', parent='BodyText', fontSize=9,
                               textColor=GRAY_700, leading=13, alignment=TA_JUSTIFY)
            h2_style    = _ps('SH2', fontSize=11, fontName='Helvetica-Bold',
                               textColor=NAVY, spaceBefore=2, spaceAfter=4, leading=14)
            h3_style    = _ps('SH3', fontSize=9.5, fontName='Helvetica-Bold',
                               textColor=GRAY_500, spaceBefore=0, spaceAfter=6, leading=12)

            # ── Helpers ───────────────────────────────────────────────
            def _section(title: str, subtitle: Optional[str] = None):
                """Accent-bar section heading (cyan left border) with optional subtitle."""
                rows = [[Paragraph(title, h2_style)]]
                if subtitle:
                    rows.append([Paragraph(subtitle, h3_style)])
                inner = Table(rows, colWidths=[6.5 * inch])
                inner.setStyle(TableStyle([
                    ('LINEBEFORE', (0, 0), (0, -1), 3, ACCENT),
                    ('LEFTPADDING',  (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING',   (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
                ]))
                return inner

            def _alt_rows(n: int, start: int = 1) -> list:
                """Alternating-row background commands."""
                cmds = []
                for i in range(start, n):
                    cmds.append(('BACKGROUND', (0, i), (-1, i),
                                  ROW_ALT if i % 2 == 0 else WHITE))
                return cmds

            def _std_header_cmds():
                return [
                    ('BACKGROUND',   (0, 0), (-1, 0), NAVY),
                    ('TEXTCOLOR',    (0, 0), (-1, 0), WHITE),
                    ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN',        (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME',     (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE',     (0, 0), (-1, -1), 9),
                    ('GRID',         (0, 0), (-1, -1), 0.35, GRAY_300),
                    ('BOX',          (0, 0), (-1, -1), 1, NAVY_MID),
                    ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING',   (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
                ]

            # ── Fetch data ────────────────────────────────────────────
            metadata       = self._get_report_metadata(session_id)
            severity       = self._query_severity_distribution(session_id)
            score_stats    = self._get_score_stats(session_id)
            top_sources    = self._get_top_sources(session_id, limit=8)
            algorithm_dist = self._get_algorithm_distribution(session_id)
            risk_level, risk_index = self._calculate_risk_index(severity)
            top_anomalies  = self._get_top_anomalies(session_id, limit=20)
            top_techniques = self._get_top_mitre_techniques(session_id, limit=10)
            mitre_summary  = self._get_mitre_summary(session_id)
            sev_total      = max(sum(severity.values()), 1)
            anomaly_rate   = (
                f"{(metadata['total_anomalies'] / metadata['total_logs'] * 100):.2f}%"
                if metadata['total_logs'] else "0.00%"
            )

            # ── Running header/footer canvas callback ─────────────────
            def _draw_page(canvas, doc, show_header: bool = True):
                canvas.saveState()
                if show_header:
                    # Navy top band
                    canvas.setFillColor(NAVY)
                    canvas.rect(0, PAGE_H - 0.48 * inch, PAGE_W, 0.48 * inch,
                                fill=1, stroke=0)
                    # Accent underline
                    canvas.setStrokeColor(ACCENT)
                    canvas.setLineWidth(1.5)
                    canvas.line(0, PAGE_H - 0.5 * inch, PAGE_W, PAGE_H - 0.5 * inch)
                    # Header text
                    canvas.setFillColor(WHITE)
                    canvas.setFont('Helvetica-Bold', 8)
                    canvas.drawString(0.75 * inch, PAGE_H - 0.3 * inch,
                                      'QUORUM - Threat Analysis Report')
                    canvas.setFont('Helvetica', 7.5)
                    canvas.drawRightString(PAGE_W - 0.75 * inch, PAGE_H - 0.3 * inch,
                                           metadata.get('generated_at', ''))
                # Footer rule
                canvas.setStrokeColor(GRAY_300)
                canvas.setLineWidth(0.5)
                canvas.line(0.75 * inch, 0.58 * inch,
                            PAGE_W - 0.75 * inch, 0.58 * inch)
                canvas.setFont('Helvetica', 7)
                canvas.setFillColor(GRAY_500)
                canvas.drawString(0.75 * inch, 0.36 * inch,
                                  'CONFIDENTIAL - For authorized personnel only')
                if show_header:
                    canvas.drawRightString(PAGE_W - 0.75 * inch, 0.36 * inch,
                                           f'Page {doc.page}')
                canvas.restoreState()

            # ── Document ──────────────────────────────────────────────
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=letter,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.8 * inch,
                bottomMargin=0.75 * inch,
            )
            elements = []

            # ════════════════════════════════════════════════════════
            # 1. COVER PAGE
            # ════════════════════════════════════════════════════════
            elements.append(Spacer(1, 1.2 * inch))
            elements.append(Paragraph('QUORUM', cover_brand))
            elements.append(Paragraph('Threat Analysis Report', cover_title))
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(HRFlowable(width='55%', color=ACCENT,
                                        thickness=1.5, hAlign='CENTER'))
            elements.append(Spacer(1, 0.25 * inch))

            if session_id:
                elements.append(Paragraph(f'Session: {session_id[:20]}', cover_sub))
            elements.append(Paragraph(f'Generated: {metadata["generated_at"]}', cover_sub))
            elements.append(Paragraph(f'Period: {metadata["analysis_period"]}', cover_sub))
            elements.append(Spacer(1, 0.7 * inch))

            # Cover KPI stat boxes
            risk_tc = T_CRITICAL if risk_level == 'HIGH' else (
                T_MEDIUM if risk_level == 'MEDIUM' else T_LOW)

            def _kpi(val, lbl, tc):
                return [
                    Paragraph(str(val),
                               _ps(f'kv_{lbl}', fontSize=20, fontName='Helvetica-Bold',
                                   textColor=tc, alignment=TA_CENTER)),
                    Paragraph(lbl, caption),
                ]

            cover_kpi = Table(
                [
                    [
                        _kpi(f"{metadata['total_logs']:,}", 'Logs Analyzed', ACCENT)[0],
                        _kpi(f"{metadata['total_anomalies']:,}", 'Anomalies', T_CRITICAL)[0],
                        _kpi(str(risk_index), f'Risk Index ({risk_level})', risk_tc)[0],
                        _kpi(f"{score_stats['avg_score']:.3f}", 'Avg Score', GRAY_700)[0],
                    ],
                    [
                        Paragraph('Logs Analyzed', caption),
                        Paragraph('Anomalies', caption),
                        Paragraph(f'Risk Index ({risk_level})', caption),
                        Paragraph('Avg Score', caption),
                    ],
                ],
                colWidths=[1.625 * inch] * 4,
            )
            cover_kpi.setStyle(TableStyle([
                ('BACKGROUND',   (0, 0), (-1, -1), GRAY_100),
                ('BOX',          (0, 0), (-1, -1), 1,   GRAY_300),
                ('INNERGRID',    (0, 0), (-1, -1), 0.5, GRAY_300),
                ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING',   (0, 0), (-1, 0),  14),
                ('BOTTOMPADDING',(0, 0), (-1, 0),  4),
                ('TOPPADDING',   (0, 1), (-1, 1),  2),
                ('BOTTOMPADDING',(0, 1), (-1, 1),  12),
            ]))
            elements.append(cover_kpi)
            elements.append(Spacer(1, 1.4 * inch))

            # Classification badge
            badge_data = [[
                Paragraph('CONFIDENTIAL - AIR-GAPPED ENVIRONMENT',
                           _ps('badge', fontSize=8, fontName='Helvetica-Bold',
                               textColor=WHITE, alignment=TA_CENTER))
            ]]
            badge = Table(badge_data, colWidths=[4 * inch])
            badge.setStyle(TableStyle([
                ('BACKGROUND',   (0, 0), (-1, -1), NAVY_MID),
                ('TOPPADDING',   (0, 0), (-1, -1), 7),
                ('BOTTOMPADDING',(0, 0), (-1, -1), 7),
                ('ALIGN',        (0, 0), (-1, -1), 'CENTER'),
            ]))
            elements.append(badge)
            elements.append(PageBreak())

            # ════════════════════════════════════════════════════════
            # 2. EXECUTIVE SUMMARY
            # ════════════════════════════════════════════════════════
            elements.append(_section('Executive Summary', 'High-level findings and risk posture'))
            elements.append(Spacer(1, 0.06 * inch))
            sum_box = Table(
                [[Paragraph(self._generate_summary(metadata), body_style)]],
                colWidths=[6.5 * inch],
            )
            sum_box.setStyle(TableStyle([
                ('BACKGROUND',   (0, 0), (-1, -1), ACCENT_LT),
                ('BOX',          (0, 0), (-1, -1), 0.75, ACCENT),
                ('LEFTPADDING',  (0, 0), (-1, -1), 12),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING',   (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING',(0, 0), (-1, -1), 10),
            ]))
            elements.append(sum_box)
            elements.append(Spacer(1, 0.18 * inch))

            # ════════════════════════════════════════════════════════
            # 3. KEY RISK INDICATORS
            # ════════════════════════════════════════════════════════
            elements.append(_section('Key Risk Indicators', 'Operational metrics and severity overview'))
            elements.append(Spacer(1, 0.06 * inch))
            kri_rows = [
                ['Metric', 'Value', 'Metric', 'Value'],
                ['Risk Level', risk_level,
                 'Risk Index (0–100)', str(risk_index)],
                ['Avg Threat Score', f"{score_stats['avg_score']:.3f}",
                 'Max Threat Score', f"{score_stats['max_score']:.3f}"],
                ['Critical + High',
                 str(severity.get('CRITICAL', 0) + severity.get('HIGH', 0)),
                 'Anomaly Rate', anomaly_rate],
                ['Total Anomalies', str(metadata['total_anomalies']),
                 'Logs Analyzed', f"{metadata['total_logs']:,}"],
            ]
            kri_table = Table(kri_rows, colWidths=[1.7*inch, 1.5*inch, 1.8*inch, 1.5*inch])
            kri_cmds = _std_header_cmds() + _alt_rows(len(kri_rows)) + [
                ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (2, 1), (2, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR',(0, 1), (-1, -1), GRAY_700),
                ('ALIGN',    (1, 1), (1, -1), 'CENTER'),
                ('ALIGN',    (3, 1), (3, -1), 'CENTER'),
            ]
            kri_table.setStyle(TableStyle(kri_cmds))
            elements.append(KeepTogether(kri_table))
            elements.append(Spacer(1, 0.18 * inch))

            # ════════════════════════════════════════════════════════
            # 4. VISUAL ANALYTICS (charts)
            # ════════════════════════════════════════════════════════
            if include_graphs:
                chart1 = self._create_severity_bar_chart(session_id)
                chart2 = self._create_score_timeline(session_id)
                chart3 = self._create_source_pie_chart(session_id)
                chart4 = self._create_mitre_bar_chart(session_id)

                elements.append(_section('Visual Analytics', 'Severity mix, trends, and MITRE coverage'))
                elements.append(Spacer(1, 0.08 * inch))

                # Severity bar + Source pie — side by side
                if chart1 or chart3:
                    cells = []
                    capts = []
                    if chart1:
                        cells.append(Image(chart1, width=3.15 * inch, height=2.4 * inch))
                        capts.append(Paragraph('Severity Distribution', caption))
                    if chart3:
                        cells.append(Image(chart3, width=3.15 * inch, height=2.4 * inch))
                        capts.append(Paragraph('Anomalies by Source', caption))

                    n = len(cells)
                    side_w = 6.5 / n * inch
                    chart_row = Table([cells], colWidths=[side_w] * n)
                    capt_row  = Table([capts], colWidths=[side_w] * n)
                    for t in (chart_row, capt_row):
                        t.setStyle(TableStyle([
                            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('LEFTPADDING',  (0, 0), (-1, -1), 2),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                        ]))
                    elements.append(chart_row)
                    elements.append(capt_row)
                    elements.append(Spacer(1, 0.12 * inch))

                # Score timeline — full width
                if chart2:
                    elements.append(Image(chart2, width=6.5 * inch, height=2.8 * inch))
                    elements.append(Paragraph('Anomaly Score Timeline', caption))
                    elements.append(Spacer(1, 0.12 * inch))

                # MITRE tactic bar — full width, dynamic height
                if chart4:
                    h = max(2.0, min(4.0, len(top_techniques or []) * 0.38 + 1.0))
                    elements.append(Image(chart4, width=6.5 * inch, height=h * inch))
                    elements.append(Paragraph('MITRE ATT&CK Tactic Distribution', caption))
                    elements.append(Spacer(1, 0.12 * inch))

            # ════════════════════════════════════════════════════════
            # 5. DETECTION BREAKDOWN
            # ════════════════════════════════════════════════════════
            elements.append(_section('Detection Breakdown', 'Severity distribution across detected anomalies'))
            elements.append(Spacer(1, 0.06 * inch))

            sev_label_colors = {
                'CRITICAL': T_CRITICAL, 'HIGH': T_HIGH,
                'MEDIUM': T_MEDIUM, 'LOW': T_LOW,
            }
            sev_rows = [['Severity', 'Count', 'Share', 'Distribution']]
            for sev in ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW'):
                cnt = severity.get(sev, 0)
                pct = cnt / sev_total * 100
                filled = max(1, int(pct / 5))
                bar = '█' * filled + '░' * (20 - filled)
                sev_rows.append([sev, str(cnt), f'{pct:.1f}%', bar])

            sev_table = Table(sev_rows, colWidths=[1.1*inch, 0.85*inch, 0.75*inch, 3.8*inch])
            sev_cmds = _std_header_cmds() + [
                ('TEXTCOLOR', (0, 1), (-1, -1), GRAY_700),
                ('ALIGN',     (1, 1), (2, -1),  'CENTER'),
            ]
            for i, sev in enumerate(('CRITICAL', 'HIGH', 'MEDIUM', 'LOW'), start=1):
                tc = sev_label_colors[sev]
                sev_cmds += [
                    ('TEXTCOLOR', (0, i), (0, i), tc),
                    ('FONTNAME',  (0, i), (0, i), 'Helvetica-Bold'),
                    ('TEXTCOLOR', (3, i), (3, i), tc),
                ]
            sev_table.setStyle(TableStyle(sev_cmds))
            elements.append(KeepTogether(sev_table))
            elements.append(Spacer(1, 0.15 * inch))

            # Algorithm contribution
            if algorithm_dist:
                elements.append(_section('Algorithm Contribution', 'Findings by detection model'))
                elements.append(Spacer(1, 0.06 * inch))
                algo_total = max(sum(a['count'] for a in algorithm_dist), 1)
                algo_rows = [['Algorithm', 'Findings', 'Share']]
                for a in algorithm_dist:
                    algo_rows.append([
                        a['algorithm'] or 'N/A',
                        str(a['count']),
                        f"{a['count'] / algo_total * 100:.1f}%",
                    ])
                algo_table = Table(algo_rows, colWidths=[3.4*inch, 1.5*inch, 1.6*inch])
                algo_table.setStyle(TableStyle(
                    _std_header_cmds()
                    + _alt_rows(len(algo_rows))
                    + [('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                       ('TEXTCOLOR', (0, 1), (-1, -1), GRAY_700)]
                ))
                elements.append(KeepTogether(algo_table))
                elements.append(Spacer(1, 0.15 * inch))

            # Top anomalous sources
            if top_sources:
                elements.append(_section('Top Anomalous Sources', 'Sources generating the most anomalies'))
                elements.append(Spacer(1, 0.06 * inch))
                src_total = max(sum(s['count'] for s in top_sources), 1)
                src_rows = [['Source', 'Count', 'Share']]
                for s in top_sources:
                    src_rows.append([
                        s['source'] or 'unknown',
                        str(s['count']),
                        f"{s['count'] / src_total * 100:.1f}%",
                    ])
                src_table = Table(src_rows, colWidths=[3.4*inch, 1.5*inch, 1.6*inch])
                src_table.setStyle(TableStyle(
                    _std_header_cmds()
                    + _alt_rows(len(src_rows))
                    + [('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                       ('TEXTCOLOR', (0, 1), (-1, -1), GRAY_700)]
                ))
                elements.append(KeepTogether(src_table))
                elements.append(Spacer(1, 0.15 * inch))

            # ════════════════════════════════════════════════════════
            # 6. TOP DETECTED THREATS  (new page)
            # ════════════════════════════════════════════════════════
            elements.append(PageBreak())
            elements.append(_section('Top Detected Threats', 'Highest scoring anomalies and context'))
            elements.append(Spacer(1, 0.06 * inch))

            if top_anomalies:
                sev_row_bg  = {'CRITICAL': C_CRITICAL, 'HIGH': C_HIGH,
                                'MEDIUM': C_MEDIUM, 'LOW': C_LOW}
                sev_row_tc  = {'CRITICAL': T_CRITICAL, 'HIGH': T_HIGH,
                                'MEDIUM': T_MEDIUM, 'LOW': T_LOW}
                thr_header  = ['Score', 'Severity', 'Source', 'MITRE ID',
                                'Tactic', 'Host', 'User', 'Timestamp']
                thr_rows    = [thr_header]
                for a in top_anomalies:
                    thr_rows.append([
                        f"{a['anomaly_score']:.3f}",
                        a['severity'],
                        (a['source'] or 'N/A')[:18],
                        (a.get('mitre_technique_id') or 'N/A')[:12],
                        (a.get('mitre_tactic') or 'N/A').replace('_', ' ').title()[:20],
                        (a.get('hostname') or 'N/A')[:14],
                        (a.get('username') or 'N/A')[:12],
                        str(a['log_timestamp'])[:16],
                    ])

                col_w = [0.55*inch, 0.72*inch, 1.1*inch,
                          0.85*inch, 1.25*inch, 0.9*inch, 0.8*inch, 1.05*inch]
                thr_table = Table(thr_rows, colWidths=col_w, repeatRows=1)
                thr_cmds = [
                    ('BACKGROUND',   (0, 0), (-1, 0), NAVY),
                    ('TEXTCOLOR',    (0, 0), (-1, 0), WHITE),
                    ('FONTNAME',     (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE',     (0, 0), (-1, 0), 8),
                    ('ALIGN',        (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME',     (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE',     (0, 1), (-1, -1), 7.5),
                    ('ALIGN',        (0, 1), (1, -1),  'CENTER'),
                    ('GRID',         (0, 0), (-1, -1), 0.3, GRAY_300),
                    ('BOX',          (0, 0), (-1, -1), 1,   NAVY_MID),
                    ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
                    ('TOPPADDING',   (0, 0), (-1, -1), 5),
                    ('BOTTOMPADDING',(0, 0), (-1, -1), 5),
                ]
                for ri, a in enumerate(top_anomalies, 1):
                    sev = a.get('severity', '')
                    thr_cmds += [
                        ('BACKGROUND', (0, ri), (-1, ri), sev_row_bg.get(sev, WHITE)),
                        ('TEXTCOLOR',  (1, ri), (1, ri),  sev_row_tc.get(sev, GRAY_700)),
                        ('FONTNAME',   (1, ri), (1, ri),  'Helvetica-Bold'),
                    ]
                thr_table.setStyle(TableStyle(thr_cmds))
                elements.append(thr_table)
                elements.append(Spacer(1, 0.2 * inch))

            # ════════════════════════════════════════════════════════
            # 7. MITRE ATT&CK
            # ════════════════════════════════════════════════════════
            if top_techniques:
                elements.append(_section('MITRE ATT&CK Techniques', 'Technique and tactic summary'))
                elements.append(Spacer(1, 0.06 * inch))
                mitre_rows = [['Technique ID', 'Tactic', 'Count']]
                for r in top_techniques:
                    mitre_rows.append([
                        r.get('mitre_technique_id') or 'N/A',
                        (r.get('mitre_tactic') or 'N/A').replace('_', ' ').title(),
                        str(r.get('count', 0)),
                    ])
                mt = Table(mitre_rows, colWidths=[1.5*inch, 3.6*inch, 1.4*inch])
                mt.setStyle(TableStyle(
                    _std_header_cmds()
                    + _alt_rows(len(mitre_rows))
                    + [('ALIGN', (2, 1), (2, -1), 'CENTER'),
                       ('TEXTCOLOR', (0, 1), (-1, -1), GRAY_700)]
                ))
                elements.append(KeepTogether(mt))
                elements.append(Spacer(1, 0.12 * inch))

            if mitre_summary and mitre_summary.get('unique_techniques', 0) > 0:
                elements.append(Paragraph(
                    f"Detected techniques span <b>{mitre_summary['unique_tactics']}</b> tactic(s) "
                    f"and <b>{mitre_summary['unique_techniques']}</b> unique technique(s) "
                    f"from the MITRE ATT&amp;CK framework.",
                    body_style,
                ))
                elements.append(Spacer(1, 0.15 * inch))

            # ════════════════════════════════════════════════════════
            # 8. RECOMMENDED ACTIONS
            # ════════════════════════════════════════════════════════
            recommendations = self._build_recommendations(severity, top_sources, top_techniques)
            if recommendations:
                elements.append(_section('Recommended Actions', 'Priority response and mitigation guidance'))
                elements.append(Spacer(1, 0.06 * inch))
                rec_rows = []
                for idx, rec in enumerate(recommendations, 1):
                    rec_rows.append([
                        Paragraph(str(idx),
                                   _ps(f'rn{idx}', fontSize=11, fontName='Helvetica-Bold',
                                       textColor=ACCENT, alignment=TA_CENTER)),
                        Paragraph(rec, body_style),
                    ])
                rec_table = Table(rec_rows, colWidths=[0.45*inch, 6.05*inch])
                rec_cmds = [
                    ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING',   (0, 0), (-1, -1), 7),
                    ('BOTTOMPADDING',(0, 0), (-1, -1), 7),
                    ('LEFTPADDING',  (1, 0), (1, -1),  8),
                    ('LINEBELOW',    (0, 0), (-1, -2),  0.3, GRAY_300),
                ] + _alt_rows(len(rec_rows), start=0)
                rec_table.setStyle(TableStyle(rec_cmds))
                elements.append(KeepTogether(rec_table))

            # ── Build ─────────────────────────────────────────────────
            doc.build(
                elements,
                onFirstPage=lambda c, d: _draw_page(c, d, show_header=False),
                onLaterPages=lambda c, d: _draw_page(c, d, show_header=True),
            )
            logger.info(f'PDF report: {output_path}')
            return output_path

        except Exception as e:
            logger.error(f'PDF report failed: {e}')
            raise ValidationError(f'Failed to generate PDF: {e}')

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
            if session_id:
                query = """
                    SELECT a.anomaly_score, a.severity, l.timestamp
                    FROM anomalies a
                    JOIN logs l ON a.log_id = l.id
                    WHERE a.detected_at >= (
                        SELECT start_time FROM analysis_sessions WHERE session_id = ?
                    )
                    AND a.detected_at <= COALESCE(
                        (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                        CURRENT_TIMESTAMP
                    )
                    ORDER BY l.timestamp
                """
                rows = db.fetch_all(query, (session_id, session_id))
            else:
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
            if session_id:
                query = """
                    SELECT l.source, COUNT(*) as count
                    FROM anomalies a
                    JOIN logs l ON a.log_id = l.id
                    WHERE a.detected_at >= (
                        SELECT start_time FROM analysis_sessions WHERE session_id = ?
                    )
                    AND a.detected_at <= COALESCE(
                        (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                        CURRENT_TIMESTAMP
                    )
                    GROUP BY l.source
                    ORDER BY count DESC
                    LIMIT 8
                """
                rows = db.fetch_all(query, (session_id, session_id))
            else:
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
            if session_id:
                query = """
                    SELECT mitre_tactic, COUNT(*) as count
                    FROM anomalies
                    WHERE mitre_tactic IS NOT NULL
                    AND detected_at >= (
                        SELECT start_time FROM analysis_sessions WHERE session_id = ?
                    )
                    AND detected_at <= COALESCE(
                        (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                        CURRENT_TIMESTAMP
                    )
                    GROUP BY mitre_tactic
                    ORDER BY count DESC
                """
                rows = db.fetch_all(query, (session_id, session_id))
            else:
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
                AND a.detected_at <= COALESCE(
                    (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                    CURRENT_TIMESTAMP
                )
                ORDER BY a.anomaly_score DESC
            """
            return db.fetch_all(query, (session_id, session_id))
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
                AND detected_at <= COALESCE(
                    (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                    CURRENT_TIMESTAMP
                )
                GROUP BY severity
            """
            rows = db.fetch_all(query, (session_id, session_id))
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
                    "(SELECT start_time FROM analysis_sessions WHERE session_id = ?) "
                    "AND detected_at <= COALESCE("
                    "(SELECT end_time FROM analysis_sessions WHERE session_id = ?), "
                    "CURRENT_TIMESTAMP)",
                    (session_id, session_id)
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
                    SELECT a.anomaly_score, a.severity, a.mitre_technique_id, a.mitre_tactic,
                           l.timestamp as log_timestamp, l.source, l.event_id, l.event_type,
                           l.hostname, l.username, a.explanation
                    FROM anomalies a JOIN logs l ON a.log_id = l.id
                    WHERE a.detected_at >= (
                        SELECT start_time FROM analysis_sessions WHERE session_id = ?
                    )
                    AND a.detected_at <= COALESCE(
                        (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                        CURRENT_TIMESTAMP
                    )
                    ORDER BY a.anomaly_score DESC LIMIT ?
                """
                return db.fetch_all(query, (session_id, session_id, limit))
            else:
                query = """
                    SELECT a.anomaly_score, a.severity, a.mitre_technique_id, a.mitre_tactic,
                           l.timestamp as log_timestamp, l.source, l.event_id, l.event_type,
                           l.hostname, l.username, a.explanation
                    FROM anomalies a JOIN logs l ON a.log_id = l.id
                    ORDER BY a.anomaly_score DESC LIMIT ?
                """
                return db.fetch_all(query, (limit,))
        except Exception as e:
            logger.error(f"Top anomalies error: {e}")
            return []

    def _get_score_stats(self, session_id: Optional[str]) -> Dict[str, float]:
        """Aggregate anomaly score statistics."""
        try:
            if session_id:
                row = db.fetch_one(
                    """
                    SELECT
                        COALESCE(AVG(anomaly_score), 0) as avg_score,
                        COALESCE(MAX(anomaly_score), 0) as max_score,
                        COALESCE(MIN(anomaly_score), 0) as min_score
                    FROM anomalies
                    WHERE detected_at >= (
                        SELECT start_time FROM analysis_sessions WHERE session_id = ?
                    )
                    AND detected_at <= COALESCE(
                        (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                        CURRENT_TIMESTAMP
                    )
                    """,
                    (session_id, session_id)
                )
            else:
                row = db.fetch_one(
                    """
                    SELECT
                        COALESCE(AVG(anomaly_score), 0) as avg_score,
                        COALESCE(MAX(anomaly_score), 0) as max_score,
                        COALESCE(MIN(anomaly_score), 0) as min_score
                    FROM anomalies
                    """
                )
            return {
                "avg_score": float(row.get("avg_score", 0) if row else 0),
                "max_score": float(row.get("max_score", 0) if row else 0),
                "min_score": float(row.get("min_score", 0) if row else 0),
            }
        except Exception as e:
            logger.error(f"Score stats error: {e}")
            return {"avg_score": 0.0, "max_score": 0.0, "min_score": 0.0}

    def _get_top_sources(self, session_id: Optional[str], limit: int = 5) -> List[Dict[str, Any]]:
        """Top anomalous log sources."""
        try:
            if session_id:
                rows = db.fetch_all(
                    """
                    SELECT COALESCE(l.source, 'unknown') as source, COUNT(*) as count
                    FROM anomalies a
                    JOIN logs l ON a.log_id = l.id
                    WHERE a.detected_at >= (
                        SELECT start_time FROM analysis_sessions WHERE session_id = ?
                    )
                    AND a.detected_at <= COALESCE(
                        (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                        CURRENT_TIMESTAMP
                    )
                    GROUP BY l.source
                    ORDER BY count DESC
                    LIMIT ?
                    """,
                    (session_id, session_id, limit),
                )
            else:
                rows = db.fetch_all(
                    """
                    SELECT COALESCE(l.source, 'unknown') as source, COUNT(*) as count
                    FROM anomalies a
                    JOIN logs l ON a.log_id = l.id
                    GROUP BY l.source
                    ORDER BY count DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            return rows or []
        except Exception as e:
            logger.error(f"Top sources error: {e}")
            return []

    def _get_algorithm_distribution(self, session_id: Optional[str]) -> List[Dict[str, Any]]:
        """Distribution of findings by algorithm."""
        try:
            if session_id:
                rows = db.fetch_all(
                    """
                    SELECT algorithm, COUNT(*) as count
                    FROM anomalies
                    WHERE detected_at >= (
                        SELECT start_time FROM analysis_sessions WHERE session_id = ?
                    )
                    AND detected_at <= COALESCE(
                        (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                        CURRENT_TIMESTAMP
                    )
                    GROUP BY algorithm
                    ORDER BY count DESC
                    """,
                    (session_id, session_id),
                )
            else:
                rows = db.fetch_all(
                    """
                    SELECT algorithm, COUNT(*) as count
                    FROM anomalies
                    GROUP BY algorithm
                    ORDER BY count DESC
                    """
                )
            return rows or []
        except Exception as e:
            logger.error(f"Algorithm distribution error: {e}")
            return []

    def _get_top_mitre_techniques(self, session_id: Optional[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Top MITRE techniques with counts."""
        try:
            if session_id:
                rows = db.fetch_all(
                    """
                    SELECT mitre_technique_id, mitre_tactic, COUNT(*) as count
                    FROM anomalies
                    WHERE mitre_technique_id IS NOT NULL
                    AND detected_at >= (
                        SELECT start_time FROM analysis_sessions WHERE session_id = ?
                    )
                    AND detected_at <= COALESCE(
                        (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                        CURRENT_TIMESTAMP
                    )
                    GROUP BY mitre_technique_id, mitre_tactic
                    ORDER BY count DESC
                    LIMIT ?
                    """,
                    (session_id, session_id, limit),
                )
            else:
                rows = db.fetch_all(
                    """
                    SELECT mitre_technique_id, mitre_tactic, COUNT(*) as count
                    FROM anomalies
                    WHERE mitre_technique_id IS NOT NULL
                    GROUP BY mitre_technique_id, mitre_tactic
                    ORDER BY count DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            return rows or []
        except Exception as e:
            logger.error(f"Top MITRE techniques error: {e}")
            return []

    def _calculate_risk_index(self, severity: Dict[str, int]) -> tuple[str, int]:
        """
        Weighted severity risk index (0-100) and label.
        Weights emphasize CRITICAL/HIGH findings.
        """
        weights = {"LOW": 1, "MEDIUM": 3, "HIGH": 6, "CRITICAL": 10}
        weighted = sum(severity.get(k, 0) * v for k, v in weights.items())
        max_weight = max(sum(severity.values()) * 10, 1)
        index = int(round((weighted / max_weight) * 100))
        if index >= 70:
            return "HIGH", index
        if index >= 40:
            return "MEDIUM", index
        return "LOW", index

    def _build_recommendations(
        self,
        severity: Dict[str, int],
        top_sources: List[Dict[str, Any]],
        top_techniques: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate short action-oriented recommendations from report findings."""
        recs: List[str] = []

        critical = severity.get('CRITICAL', 0)
        high = severity.get('HIGH', 0)
        if critical > 0:
            recs.append(
                f"Prioritize triage of {critical} CRITICAL anomaly/anomalies within 24 hours and isolate affected endpoints immediately."
            )
        if high > 0:
            recs.append(
                f"Investigate {high} HIGH-severity finding(s) and validate whether they indicate active lateral movement or privilege misuse."
            )

        if top_sources:
            recs.append(
                f"Increase logging and detection coverage for top source '{top_sources[0]['source']}' which produced {top_sources[0]['count']} anomaly/anomalies."
            )

        if top_techniques:
            t = top_techniques[0]
            tech = t.get('mitre_technique_id') or 'N/A'
            tactic = (t.get('mitre_tactic') or 'unknown').replace('_', ' ')
            recs.append(
                f"Map incident-response playbooks to MITRE {tech} ({tactic}) and run targeted containment drills for this pattern."
            )

        recs.append("Schedule rule/model tuning to reduce false positives while preserving coverage on HIGH and CRITICAL detections.")
        return recs[:5]

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
                    AND detected_at <= COALESCE(
                        (SELECT end_time FROM analysis_sessions WHERE session_id = ?),
                        CURRENT_TIMESTAMP
                    )
                """, (session_id, session_id))
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

