import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import quote

from dotenv import load_dotenv


load_dotenv()
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
def _get_backend_url():
    if os.getenv("BACKEND_URL"):
        return os.getenv("BACKEND_URL").rstrip("/")
    if os.getenv("RAILWAY_PUBLIC_DOMAIN"):
        return f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN').rstrip('/')}"
    return "http://localhost:8000"


def _get_frontend_url():
    if os.getenv("FRONTEND_URL"):
        return os.getenv("FRONTEND_URL").rstrip("/")
    frontend_urls = os.getenv("FRONTEND_URLS", "")
    if frontend_urls:
        first_url = frontend_urls.split(",")[0].strip()
        if first_url and first_url != "*":
            return first_url.rstrip("/")
    return "http://localhost:5173"


def _send_email(target_email: str, subject: str, text: str, html: str) -> bool:
    smtp_email = os.getenv("SMTP_EMAIL") or SMTP_EMAIL
    smtp_password = os.getenv("SMTP_PASSWORD") or SMTP_PASSWORD
    if not smtp_email or not smtp_password:
        return False
    # Strip spaces if app password had spaces formatted
    smtp_password = smtp_password.replace(" ", "").strip()
    smtp_email = smtp_email.strip()

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = smtp_email
    message["To"] = target_email
    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))

    # Try Port 587 (TLS - Cloud standard) first, fallback to Port 465 (SSL)
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, target_email, message.as_string())
        return True
    except (smtplib.SMTPException, OSError):
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
                server.login(smtp_email, smtp_password)
                server.sendmail(smtp_email, target_email, message.as_string())
            return True
        except (smtplib.SMTPException, OSError):
            return False


def send_verification_email(target_email: str, token: str):
    verify_link = f"{_get_backend_url()}/verify?token={quote(token, safe='')}"
    return _send_email(
        target_email,
        "Verify your CheckMate Account",
        f"Verify your email address by opening this link:\n{verify_link}",
        f'<html><body><h2>Welcome to CheckMate!</h2><p>Verify your email address:</p><a href="{verify_link}">Verify Email</a></body></html>',
    )


def send_password_reset_email(target_email: str, token: str):
    # Fragments are never included in HTTP Referer headers or server access logs.
    reset_link = f"{_get_frontend_url()}/#reset_token={quote(token, safe='')}"
    return _send_email(
        target_email,
        "Reset your CheckMate Password",
        f"Reset your password by opening this link:\n{reset_link}\nThis link expires in one hour.",
        f'<html><body><h2>Reset Your Password</h2><p><a href="{reset_link}">Reset Password</a></p><p>This link expires in one hour.</p></body></html>',
    )
