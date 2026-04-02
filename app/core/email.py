import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def sync_send_smtp_email(to_email: str, subject: str, html_content: str) -> bool:
    """
    Synchronous helper to send email via SMTP.
    """
    msg = MIMEMultipart()
    msg["From"] = settings.mail_from
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(settings.mail_server, settings.mail_port) as server:
            server.starttls()  # Secure the connection
            server.login(settings.mail_username, settings.mail_password)
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"SMTP error sending to {to_email}: {str(e)}")
        return False


async def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Sends a 6-digit OTP code to the requested email.
    In local dev (if no MAIL_PASSWORD is found), it prints the OTP to the console.
    """
    if not settings.mail_password:
        print("\n" + "=" * 50)
        print("MOCK DEV EMAIL DISPATCH")
        print(f"To: {to_email}")
        print(f"Code: ** {otp_code} **")
        print("=" * 50 + "\n")
        return True

    h1_style = (
        "background: #f4f4f4; padding: 10px; "
        "text-align: center; letter-spacing: 5px;"
    )
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2>Password Reset Code</h2>
        <p>A password reset was requested for your account.</p>
        <p>Your 6-digit verification code is:</p>
        <h1 style="{h1_style}">{otp_code}</h1>
        <p>This code will expire in 10 minutes.</p>
        <p>If you did not request this, please ignore this email.</p>
    </div>
    """

    # Run the blocking SMTP call in a separate thread to keep FastAPI responsive
    success = await asyncio.to_thread(
        sync_send_smtp_email, to_email, "Your Password Reset Code", html_content
    )

    if success:
        logger.info(f"SMTP dispatched OTP to {to_email}")
    return success
