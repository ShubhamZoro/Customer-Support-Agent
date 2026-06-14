"""
services/email_service.py — Send refund confirmation emails.

In dev mode (SMTP_HOST not configured), emails are printed to stdout.
In production, set SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD / EMAIL_FROM in .env.
"""
import smtplib
import textwrap
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import settings


def _build_html(user_email: str, order_id: str, product_category: str,
                product_price: float, order_quantity: int,
                discount_applied: float, payment_method: str, reason: str) -> str:
    refund_amount = round((product_price * order_quantity) - discount_applied, 2)
    today = datetime.now().strftime("%B %d, %Y")

    timeline = {
        "Credit Card": "5–10 business days",
        "Debit Card": "3–5 business days",
        "PayPal": "1–3 business days",
    }.get(payment_method, "3–7 business days")

    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto">
      <div style="background:#4f46e5;padding:24px;border-radius:8px 8px 0 0">
        <h1 style="color:#fff;margin:0;font-size:22px">ShopWave — Refund Initiated</h1>
      </div>
      <div style="border:1px solid #e5e7eb;padding:24px;border-radius:0 0 8px 8px">
        <p>Hi <strong>{user_email}</strong>,</p>
        <p>Your refund request has been received and is now being processed.</p>

        <table style="width:100%;border-collapse:collapse;margin:16px 0">
          <tr style="background:#f3f4f6">
            <td style="padding:10px 14px;font-weight:bold">Order ID</td>
            <td style="padding:10px 14px">{order_id}</td>
          </tr>
          <tr>
            <td style="padding:10px 14px;font-weight:bold">Category</td>
            <td style="padding:10px 14px">{product_category}</td>
          </tr>
          <tr style="background:#f3f4f6">
            <td style="padding:10px 14px;font-weight:bold">Refund Amount</td>
            <td style="padding:10px 14px"><strong>${refund_amount:.2f} USD</strong></td>
          </tr>
          <tr>
            <td style="padding:10px 14px;font-weight:bold">Return Reason</td>
            <td style="padding:10px 14px">{reason}</td>
          </tr>
          <tr style="background:#f3f4f6">
            <td style="padding:10px 14px;font-weight:bold">Payment Method</td>
            <td style="padding:10px 14px">{payment_method}</td>
          </tr>
          <tr>
            <td style="padding:10px 14px;font-weight:bold">Processing Time</td>
            <td style="padding:10px 14px">{timeline}</td>
          </tr>
          <tr style="background:#f3f4f6">
            <td style="padding:10px 14px;font-weight:bold">Date Initiated</td>
            <td style="padding:10px 14px">{today}</td>
          </tr>
        </table>

        <p style="background:#fef9c3;border-left:4px solid #eab308;padding:12px 16px;border-radius:4px">
          <strong>Note:</strong> The refund will be credited back to your {payment_method} within {timeline}.
        </p>

        <p>If you have any questions, reply to this email or contact our support team.</p>
        <p style="color:#6b7280;font-size:12px;margin-top:32px">
          This is an automated message from ShopWave Support · {today}
        </p>
      </div>
    </body></html>
    """


def send_refund_initiated_email(
    to_email: str,
    order_id: str,
    product_category: str,
    product_price: float,
    order_quantity: int,
    discount_applied: float,
    payment_method: str,
    reason: str,
) -> bool:
    """
    Send a refund confirmation email.
    Returns True on success (or dev-mode print), False on SMTP error.
    """
    subject = f"ShopWave — Refund Initiated for Order {order_id}"
    html_body = _build_html(
        to_email, order_id, product_category,
        product_price, order_quantity, discount_applied,
        payment_method, reason,
    )
    refund_amount = round((product_price * order_quantity) - discount_applied, 2)

    # ── Dev mode: no SMTP configured ────────────────────────────────────────
    if not settings.SMTP_HOST:
        print("\n" + "=" * 60)
        print("📧  [DEV MODE] Refund Email (would be sent in production)")
        print("=" * 60)
        print(f"  To      : {to_email}")
        print(f"  Subject : {subject}")
        print(f"  Order   : {order_id}")
        print(f"  Refund  : ${refund_amount:.2f} | {payment_method}")
        print(f"  Reason  : {reason}")
        print("=" * 60 + "\n")
        return True

    # ── Production SMTP ──────────────────────────────────────────────────────
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to_email

        text_part = textwrap.dedent(f"""
            Refund Initiated — {order_id}
            Refund Amount : ${refund_amount:.2f} USD
            Reason        : {reason}
            Payment Method: {payment_method}
        """)
        msg.attach(MIMEText(text_part, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, [to_email], msg.as_string())
        return True
    except Exception as exc:
        print(f"[email_service] SMTP error: {exc}")
        return False
