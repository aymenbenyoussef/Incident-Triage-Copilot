from datetime import datetime, timezone

from agent.report import create_pdf_report, parse_report


def test_parse_report_sections():
    sections = parse_report(
        "INCIDENT SUMMARY: Checkout failures are affecting the API.\n"
        "SEVERITY: High.\n"
        "AFFECTED SERVICES: api, web.\n"
        "TIMELINE: Error started after deployment.\n"
        "ROOT CAUSE: Bad deployment.\n"
        "CONFIDENCE: High.\n"
        "EVIDENCE:\n- Error rate increased.\n- Latency increased.\n"
        "CUSTOMER IMPACT: Checkout requests fail.\n"
        "RECOMMENDED ACTION: Roll back the deployment.\n"
        "FOLLOW-UP INVESTIGATION: Confirm error rates after rollback."
    )

    assert sections["INCIDENT SUMMARY"] == "Checkout failures are affecting the API."
    assert sections["SEVERITY"] == "High."
    assert sections["AFFECTED SERVICES"] == "api, web."
    assert sections["TIMELINE"] == "Error started after deployment."
    assert sections["ROOT CAUSE"] == "Bad deployment."
    assert sections["CONFIDENCE"] == "High."
    assert sections["EVIDENCE"] == "- Error rate increased.\n- Latency increased."
    assert sections["CUSTOMER IMPACT"] == "Checkout requests fail."
    assert sections["RECOMMENDED ACTION"] == "Roll back the deployment."
    assert sections["FOLLOW-UP INVESTIGATION"] == "Confirm error rates after rollback."


def test_parse_unstructured_report():
    sections = parse_report("Investigation was inconclusive.")
    assert sections["INCIDENT SUMMARY"] == "Investigation was inconclusive."
    assert sections["FOLLOW-UP INVESTIGATION"] == "Not provided."


def test_create_pdf_report_uses_timestamped_filename(tmp_path):
    generated_at = datetime(2026, 10, 18, 17, 30, 0, 123456, tzinfo=timezone.utc)
    report_path = create_pdf_report(
        "The API is slow.",
        "ROOT CAUSE: Bad deployment.",
        tool_calls=3,
        output_dir=tmp_path,
        generated_at=generated_at,
    )

    assert report_path.name == "incident-report-20261018-173000-123456.pdf"
    assert report_path.parent == tmp_path
    assert report_path.read_bytes().startswith(b"%PDF")
