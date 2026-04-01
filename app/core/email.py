import logging

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)

if settings.resend_api_key:
    resend.api_key = settings.resend_api_key


async def send_otp_email(to_email: str, otp_code: str) -> bool:
    """
    Sends a 6-digit OTP code to the requested email.
    In local dev (if no RESEND_API_KEY is found), it prints the OTP to the console.
    """
    if not settings.resend_api_key:
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

    try:
        # Note: In Resend free-tier sandbox, you can ONLY send emails to the exact same
        # domain/email address that verified the sender! Keep this in mind!
        response = resend.Emails.send(
            {
                "from": "Acme <onboarding@resend.dev>",
                "to": [to_email],
                "subject": "Your Password Reset Code",
                "html": html_content,
            }
        )
        logger.info(f"Resend dispatched OTP to {to_email}. ID: {response.get('id')}")
        return True
    except Exception as e:
        logger.error(f"Failed to send resend email to {to_email}: {str(e)}")
        # In production we might not want to throw a 500, but rather return False
        # so the router can throw a specific 502 Bad Gateway.
        return False
