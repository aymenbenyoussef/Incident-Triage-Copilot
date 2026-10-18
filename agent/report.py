from __future__ import annotations

import re
from datetime import datetime
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

REPORT_SECTIONS = (
    "INCIDENT SUMMARY",
    "SEVERITY",
    "AFFECTED SERVICES",
    "TIMELINE",
    "ROOT CAUSE",
    "CONFIDENCE",
    "EVIDENCE",
    "CUSTOMER IMPACT",
    "RECOMMENDED ACTION",
    "FOLLOW-UP INVESTIGATION",
)
SECTION_PATTERN = re.compile(
    r"(?im)^(INCIDENT SUMMARY|SEVERITY|AFFECTED SERVICES|TIMELINE|"
    r"ROOT CAUSE|CONFIDENCE|EVIDENCE|CUSTOMER IMPACT|RECOMMENDED ACTION|"
    r"FOLLOW-UP INVESTIGATION):\s*"
)


def parse_report(report_text: str) -> dict[str, str]:
    """Parse the agent's labelled report while preserving unlabelled output."""
    matches = list(SECTION_PATTERN.finditer(report_text))
    if not matches:
        sections = {section: "Not provided." for section in REPORT_SECTIONS}
        sections["INCIDENT SUMMARY"] = report_text.strip() or "No report was returned."
        return sections

    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(report_text)
        value = report_text[start:end].strip()
        sections[match.group(1).upper()] = value or "Not provided."

    prefix = report_text[:matches[0].start()].strip()
    if prefix and "INCIDENT SUMMARY" not in sections:
        sections["INCIDENT SUMMARY"] = prefix

    for section in REPORT_SECTIONS:
        sections.setdefault(section, "Not provided.")

    return {section: sections[section] for section in REPORT_SECTIONS}


def _paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    safe_text = escape(text).replace("\n", "<br/>")
    return Paragraph(safe_text, style)


def _footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#667085"))
    canvas.drawString(0.75 * inch, 0.45 * inch, "Incident Triage Copilot")
    canvas.drawRightString(7.75 * inch, 0.45 * inch, f"Page {document.page}")
    canvas.restoreState()


def create_pdf_report(
    problem: str,
    report_text: str,
    tool_calls: int,
    output_dir: str | Path = "reports",
    generated_at: datetime | None = None,
) -> Path:
    """Create and return a timestamped PDF incident report."""
    created = generated_at or datetime.now().astimezone()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    filename = f"incident-report-{created.strftime('%Y%m%d-%H%M%S-%f')}.pdf"
    report_path = output_path / filename

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#123B5D"),
        spaceAfter=18,
    )
    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#123B5D"),
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        leading=15,
        spaceAfter=8,
    )
    small_style = ParagraphStyle(
        "ReportSmall",
        parent=body_style,
        fontSize=9,
        leading=12,
    )

    story = [
        Paragraph("Incident Investigation Report", title_style),
        Table(
            [
                [_paragraph("Generated", small_style), _paragraph(created.isoformat(), small_style)],
                [_paragraph("Investigation request", small_style), _paragraph(problem, small_style)],
                [_paragraph("Tool calls", small_style), _paragraph(str(tool_calls), small_style)],
            ],
            colWidths=[1.55 * inch, 5.45 * inch],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF2F8")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#B8C7D1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E2E8")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            ),
        ),
        Spacer(1, 10),
    ]

    for section, content in parse_report(report_text).items():
        story.extend(
            [
                Paragraph(escape(section.title()), heading_style),
                _paragraph(content, body_style),
            ]
        )

    SimpleDocTemplate(
        str(report_path),
        pagesize=LETTER,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="Incident Investigation Report",
        author="Incident Triage Copilot",
    ).build(story, onFirstPage=_footer, onLaterPages=_footer)
    return report_path
