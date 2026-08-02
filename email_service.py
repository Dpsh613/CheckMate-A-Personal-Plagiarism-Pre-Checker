import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

from dotenv import load_dotenv


load_dotenv()
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def _send_email(target_email: str, subject: str, text: str, html: str) -> bool:
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        return False
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SMTP_EMAIL
    message["To"] = target_email
    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, target_email, message.as_string())
        return True
    except (smtplib.SMTPException, OSError):
        return False


def send_verification_email(target_email: str, token: str):
    verify_link = f"{BACKEND_URL}/verify?token={quote(token, safe='')}"
    return _send_email(
        target_email,
        "Verify your CheckMate Account",
        f"Verify your email address by opening this link:\n{verify_link}",
        f'<html><body><h2>Welcome to CheckMate!</h2><p>Verify your email address:</p><a href="{verify_link}">Verify Email</a></body></html>',
    )


def send_password_reset_email(target_email: str, token: str):
    # Fragments are never included in HTTP Referer headers or server access logs.
    reset_link = f"{FRONTEND_URL}/#reset_token={quote(token, safe='')}"
    return _send_email(
        target_email,
        "Reset your CheckMate Password",
        f"Reset your password by opening this link:\n{reset_link}\nThis link expires in one hour.",
        f'<html><body><h2>Reset Your Password</h2><p><a href="{reset_link}">Reset Password</a></p><p>This link expires in one hour.</p></body></html>',
    )
