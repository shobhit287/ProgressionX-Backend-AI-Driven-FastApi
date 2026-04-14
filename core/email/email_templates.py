"""HTML + plain-text email templates."""

from datetime import date
from typing import Optional


def export_report_email(
    *,
    first_name: str,
    start_date: date,
    end_date: date,
    split_name: Optional[str],
    exercise_name: Optional[str],
) -> tuple[str, str, str]:
    """Return (subject, html_body, text_body) for the export-report email."""
    subject = f"Your ProgressionX report · {start_date} to {end_date}"

    scope_bits = [f"{start_date} → {end_date}"]
    if split_name:
        scope_bits.append(f"Split: {split_name}")
    if exercise_name:
        scope_bits.append(f"Exercise: {exercise_name}")
    scope = " · ".join(scope_bits)

    html_body = f"""<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#0f172a;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#e2e8f0;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;padding:32px 16px;">
      <tr>
        <td align="center">
          <table width="560" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:16px;border:1px solid #334155;overflow:hidden;">
            <tr>
              <td style="padding:28px 32px 12px 32px;">
                <h1 style="margin:0;font-size:22px;color:#f8fafc;">Your performance report is ready</h1>
                <p style="margin:8px 0 0 0;font-size:14px;color:#94a3b8;">{scope}</p>
              </td>
            </tr>
            <tr>
              <td style="padding:8px 32px 24px 32px;font-size:15px;line-height:22px;color:#cbd5e1;">
                <p>Hi {first_name},</p>
                <p>
                  Your ProgressionX performance report for the selected range is attached as a PDF.
                  It includes summary metrics, volume trends, top-exercise breakdowns, and an
                  AI-written summary with personalized suggestions based on your training.
                </p>
                <p style="color:#94a3b8;font-size:13px;margin-top:20px;">
                  Keep training smart — see you in the next session.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:16px 32px;border-top:1px solid #334155;font-size:12px;color:#64748b;">
                Sent automatically by ProgressionX. Reply is not monitored.
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""

    text_body = (
        f"Hi {first_name},\n\n"
        f"Your ProgressionX performance report is attached as a PDF.\n"
        f"Scope: {scope}\n\n"
        "It includes summary metrics, charts, and an AI-written summary with "
        "personalized suggestions.\n\n"
        "— ProgressionX"
    )

    return subject, html_body, text_body
