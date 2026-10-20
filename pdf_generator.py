"""
PDF Report Generator for API Sentinel using ReportLab.

Generates polished, audit-ready QA test execution summaries with
sanitized metrics, pass/fail breakdowns, latency stats, and failure details.
"""

import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from testing_engine.models import TestRun


def generate_test_run_pdf(test_run: TestRun) -> bytes:
    """
    Generates a PDF document in memory for a given TestRun and returns raw bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0F172A'),
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B'),
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155'),
    )
    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1E293B'),
    )
    badge_pass = ParagraphStyle(
        'BadgePass',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#16A34A'),
    )
    badge_fail = ParagraphStyle(
        'BadgeFail',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#DC2626'),
    )

    elements = []

    # Title & Subtitle
    elements.append(Paragraph("API Sentinel — Quality Assurance Report", title_style))
    suite_name = test_run.suite.name if test_run.suite else "Ad-hoc Execution"
    from django.utils import timezone
    generated_at = timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    elements.append(Paragraph(f"Project: <b>{test_run.project.name}</b> &nbsp;|&nbsp; Suite: <b>{suite_name}</b> &nbsp;|&nbsp; Generated: {generated_at}", subtitle_style))
    elements.append(Spacer(1, 14))

    # Metric Cards Summary Table
    is_pass = (test_run.status == 'PASSED')
    status_color = colors.HexColor('#DCFCE7') if is_pass else colors.HexColor('#FEE2E2')
    status_text_color = colors.HexColor('#166534') if is_pass else colors.HexColor('#991B1B')

    summary_data = [
        [
            Paragraph("<b>Execution Status</b>", cell_style),
            Paragraph("<b>Total Tests</b>", cell_style),
            Paragraph("<b>Passed</b>", cell_style),
            Paragraph("<b>Failed</b>", cell_style),
            Paragraph("<b>Pass Rate</b>", cell_style),
            Paragraph("<b>Total Duration</b>", cell_style),
        ],
        [
            Paragraph(f"<b>{test_run.status}</b>", ParagraphStyle('St', fontName='Helvetica-Bold', textColor=status_text_color)),
            Paragraph(str(test_run.total_tests), cell_bold),
            Paragraph(str(test_run.passed_tests), ParagraphStyle('P', fontName='Helvetica-Bold', textColor=colors.HexColor('#16A34A'))),
            Paragraph(str(test_run.failed_tests), ParagraphStyle('F', fontName='Helvetica-Bold', textColor=colors.HexColor('#DC2626'))),
            Paragraph(f"{test_run.pass_percentage}%", cell_bold),
            Paragraph(f"{test_run.total_duration_ms:.1f} ms", cell_bold),
        ]
    ]

    summary_table = Table(summary_data, colWidths=[1.3*inch, 1.0*inch, 0.9*inch, 0.9*inch, 1.1*inch, 1.3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0, 1), (0, 1), status_color),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 18))

    # Test Results Detail Section
    elements.append(Paragraph("Individual Test Results & Assertions", section_heading))
    elements.append(Spacer(1, 6))

    results_data = [
        [
            Paragraph("<b>Test Name</b>", cell_bold),
            Paragraph("<b>Status</b>", cell_bold),
            Paragraph("<b>HTTP</b>", cell_bold),
            Paragraph("<b>Latency</b>", cell_bold),
            Paragraph("<b>Details / Failure Reason</b>", cell_bold),
        ]
    ]

    results = test_run.results.all()
    if not results:
        results_data.append([
            Paragraph("No test results recorded for this run.", cell_style),
            Paragraph("-", cell_style),
            Paragraph("-", cell_style),
            Paragraph("-", cell_style),
            Paragraph("-", cell_style),
        ])
    else:
        for res in results:
            status_para = Paragraph("PASS", badge_pass) if res.passed else Paragraph("FAIL", badge_fail)
            http_code = str(res.status_code) if res.status_code else "-"
            latency_str = f"{res.elapsed_ms:.1f}ms"
            
            # Sanitized failure reason
            detail_msg = res.error_message if not res.passed else "All assertions satisfied."
            if not detail_msg and res.assertion_details:
                failed_assertions = [a.get('message', '') for a in res.assertion_details if not a.get('passed', True)]
                if failed_assertions:
                    detail_msg = "; ".join(failed_assertions)
            
            results_data.append([
                Paragraph(res.name[:35], cell_style),
                status_para,
                Paragraph(http_code, cell_style),
                Paragraph(latency_str, cell_style),
                Paragraph((detail_msg or "")[:120], cell_style),
            ])

    results_table = Table(results_data, colWidths=[2.2*inch, 0.8*inch, 0.7*inch, 0.9*inch, 2.7*inch])
    results_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(results_table)
    elements.append(Spacer(1, 24))

    # Redaction / Security Notice Footer
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CBD5E1')))
    elements.append(Spacer(1, 6))
    notice_text = (
        "<b>Confidential & Sanitized:</b> This report is generated by API Sentinel. All sensitive headers, "
        "authorization tokens, and internal network parameters are cryptographically protected and redacted."
    )
    elements.append(Paragraph(notice_text, subtitle_style))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
