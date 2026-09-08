import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger("app.email_service")

# Virtual email logs for developer console & dashboard review
virtual_email_logs: List[Dict[str, Any]] = []


def get_virtual_email_logs() -> List[Dict[str, Any]]:
    return virtual_email_logs


def clear_virtual_email_logs():
    virtual_email_logs.clear()


def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """
    Sends an email using standard SMTP.
    If SMTP credentials are not configured or sending fails, it gracefully falls back
    to the Virtual Email gateway and records the full message in-memory for testing.
    """
    timestamp = datetime.utcnow().isoformat()
    from_name = settings.SMTP_FROM_NAME
    from_email = settings.SMTP_FROM_EMAIL or "noreply@emergency-response.gov.in"

    # 1. Try sending via Real SMTP if configured
    if settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD:
        try:
            logger.info(f"Connecting to SMTP server {settings.SMTP_HOST}:{settings.SMTP_PORT} to send email to {to_email}...")
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = to_email

            if text_body:
                msg.attach(MIMEText(text_body, "plain", "utf-8"))
            if html_body:
                msg.attach(MIMEText(html_body, "html", "utf-8"))

            if settings.SMTP_PORT == 465:
                server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
            else:
                server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
                if settings.SMTP_TLS:
                    server.starttls()

            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(from_email, [to_email], msg.as_string())
            server.quit()

            logger.info(f"Email successfully delivered to {to_email} via SMTP.")
            virtual_email_logs.append({
                "to_email": to_email,
                "subject": subject,
                "timestamp": timestamp,
                "gateway": "smtp",
                "status": "delivered",
                "preview": text_body[:160] if text_body else "HTML Content"
            })
            return True
        except Exception as err:
            logger.error(f"SMTP delivery failed: {err}. Falling back to virtual email gateway.")

    # 2. Virtual fallback gateway
    virtual_email_logs.append({
        "to_email": to_email,
        "subject": subject,
        "timestamp": timestamp,
        "gateway": "virtual_fallback",
        "status": "sent (simulation)",
        "preview": text_body[:160] if text_body else "HTML Content"
    })
    if len(virtual_email_logs) > 500:
        virtual_email_logs.pop(0)

    print("\n" + "=" * 65)
    print(f"[EMAIL SERVICE - VIRTUAL GATEWAY]")
    print(f"To: {to_email}")
    print(f"From: {from_name} <{from_email}>")
    print(f"Subject: {subject}")
    print(f"Time: {timestamp} UTC")
    print("-" * 65)
    print(text_body or html_body)
    print("=" * 65 + "\n")
    return True


def send_otp_email(to_email: str, name: str, otp_code: str) -> bool:
    """
    Sends the 6-digit verification OTP email for family account signup.
    """
    subject = f"Your Verification OTP: {otp_code} - Government Emergency Portal"
    
    text_body = f"""Dear {name},

Your one-time verification code for registering with the Government Emergency Portal is:

  >>> {otp_code} <<<

This code is valid for 10 minutes. Do not share this OTP with anyone.

If you did not request this code, please ignore this email.

National Emergency Response & Telemetry Infrastructure
For emergency assistance, dial 112 immediately.
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f0f4f8; margin: 0; padding: 20px; }}
    .card {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #bfdbfe; box-shadow: 0 4px 16px rgba(30, 58, 138, 0.08); }}
    .header {{ background: #1e3a8a; padding: 24px; text-align: center; color: #ffffff; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 800; letter-spacing: 0.5px; text-transform: uppercase; }}
    .header p {{ margin: 6px 0 0; font-size: 12px; color: #93c5fd; font-weight: 600; letter-spacing: 1px; }}
    .content {{ padding: 32px 28px; color: #1e293b; }}
    .otp-box {{ margin: 24px 0; background: #eff6ff; border: 2px dashed #2563eb; border-radius: 10px; padding: 18px; text-align: center; }}
    .otp-code {{ font-size: 36px; font-weight: 900; letter-spacing: 8px; color: #1e3a8a; font-family: monospace; }}
    .notice {{ font-size: 13px; color: #64748b; line-height: 1.6; margin-top: 20px; }}
    .footer {{ background: #f8fafc; padding: 18px 28px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; }}
    .badge {{ display: inline-block; background: #dc2626; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <p>CENTRAL EMERGENCY DISPATCH PORTAL</p>
      <h1>Verification Code</h1>
    </div>
    <div class="content">
      <p style="font-size: 15px; margin-top: 0;">Hello <strong>{name}</strong>,</p>
      <p style="font-size: 14px; color: #475569; line-height: 1.5;">
        You are verifying your identity to create a Family Incident Tracking account. Please enter the following 6-digit OTP to complete your verification:
      </p>
      <div class="otp-box">
        <div class="otp-code">{otp_code}</div>
        <p style="margin: 8px 0 0; font-size: 12px; font-weight: 700; color: #2563eb;">Valid for 10 minutes</p>
      </div>
      <p class="notice">
        <strong>Security Notice:</strong> Never share your one-time password with anyone, including government personnel or emergency dispatchers.
      </p>
    </div>
    <div class="footer">
      Government Accident Detection & Alert System &bull; In life-threatening emergencies, dial <span class="badge">112</span>
    </div>
  </div>
</body>
</html>
"""
    return send_email(to_email, subject, html_body, text_body)


def send_welcome_email(to_email: str, name: str, plate_number: str, contact_name: str = "", relation: str = "") -> bool:
    """
    Sends the official confirmation email after successful family account signup.
    """
    subject = "Signup Successful - Government Emergency Portal Family Access"
    
    text_body = f"""Dear {name},

Your registration for the Government Emergency Portal has been COMPLETED SUCCESSFULLY.

Account Summary:
---------------------------------------------
Account Holder   : {name}
Registered Email : {to_email}
Linked Vehicle   : {plate_number}
{f"Emergency Contact: {contact_name} ({relation})" if contact_name else ""}
Access Level     : Family Accident Status & Telemetry
---------------------------------------------

What you can do now:
- View real-time accident status for vehicle {plate_number}
- Monitor emergency responder dispatch (Police & Medical Trauma Units)
- Access GPS location and severity information if an incident occurs

Portal URL: {settings.CORS_ORIGINS.split(',')[0]}

National Emergency Response & Telemetry Infrastructure
In any emergency, contact 112 immediately.
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #f0f4f8; margin: 0; padding: 20px; }}
    .card {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #bfdbfe; box-shadow: 0 4px 16px rgba(30, 58, 138, 0.08); }}
    .header {{ background: #1e3a8a; padding: 28px 24px; text-align: center; color: #ffffff; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 900; letter-spacing: 0.5px; text-transform: uppercase; }}
    .header p {{ margin: 6px 0 0; font-size: 12px; color: #93c5fd; font-weight: 600; letter-spacing: 1px; }}
    .content {{ padding: 32px 28px; color: #1e293b; }}
    .success-badge {{ background: #ecfdf5; border: 1px solid #a7f3d0; color: #047857; border-radius: 8px; padding: 14px 16px; margin-bottom: 24px; font-size: 14px; font-weight: 700; display: flex; align-items: center; }}
    .details-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; background: #f8fafc; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }}
    .details-table td {{ padding: 12px 16px; font-size: 13px; border-bottom: 1px solid #e2e8f0; }}
    .details-table td.label {{ font-weight: 700; color: #64748b; width: 40%; text-transform: uppercase; font-size: 11px; }}
    .details-table td.val {{ font-weight: 800; color: #1e3a8a; }}
    .btn {{ display: inline-block; background: #1e3a8a; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: 800; font-size: 14px; margin-top: 16px; text-align: center; }}
    .footer {{ background: #f8fafc; padding: 18px 28px; border-top: 1px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-align: center; }}
    .badge {{ display: inline-block; background: #dc2626; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 11px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <p>CENTRAL EMERGENCY DISPATCH PORTAL</p>
      <h1>Account Activated</h1>
    </div>
    <div class="content">
      <div class="success-badge">
        &#10004;&nbsp; Family Emergency Account Verified & Activated Successfully!
      </div>
      <p style="font-size: 15px; margin-top: 0;">Dear <strong>{name}</strong>,</p>
      <p style="font-size: 14px; color: #475569; line-height: 1.6;">
        Your identity and emergency contact registration have been verified. You now have authorized access to view real-time incident responses and emergency telemetry for your family's vehicle.
      </p>

      <table class="details-table">
        <tr>
          <td class="label">Account Name</td>
          <td class="val">{name}</td>
        </tr>
        <tr>
          <td class="label">Registered Email</td>
          <td class="val">{to_email}</td>
        </tr>
        <tr>
          <td class="label">Linked Vehicle</td>
          <td class="val" style="color: #2563eb;">{plate_number}</td>
        </tr>
        {f'<tr><td class="label">Relation Record</td><td class="val">{contact_name} ({relation})</td></tr>' if contact_name else ''}
        <tr>
          <td class="label">Authorization</td>
          <td class="val" style="color: #16a34a;">Family Support Granted</td>
        </tr>
      </table>

      <p style="font-size: 13px; color: #64748b; line-height: 1.5;">
        You can log in at any time to check vehicle status and view police or hospital dispatch logs.
      </p>
    </div>
    <div class="footer">
      Government Accident Detection & Alert System &bull; In life-threatening emergencies, dial <span class="badge">112</span>
    </div>
  </div>
</body>
</html>
"""
    return send_email(to_email, subject, html_body, text_body)
