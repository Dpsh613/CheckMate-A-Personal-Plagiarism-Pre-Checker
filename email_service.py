import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_verification_email(target_email, token):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("SMTP Credentials not configured.")
        return False
        
    sender_email = SMTP_EMAIL
    receiver_email = target_email

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your CheckMate Account"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    verify_link = f"http://localhost:8000/verify?token={token}"

    text = f"Hi there!\n\nPlease verify your email for CheckMate by clicking this link:\n{verify_link}"
    html = f"""\
    <html>
      <body>
        <h2>Welcome to CheckMate!</h2>
        <p>Please click the button below to verify your email address:</p>
        <a href="{verify_link}" style="display:inline-block;padding:10px 20px;background-color:#4f46e5;color:white;text-decoration:none;border-radius:5px;">Verify Email</a>
        <p><br>If the button doesn't work, copy and paste this link:<br>{verify_link}</p>
      </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, SMTP_PASSWORD)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def send_password_reset_email(target_email, token):
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("SMTP Credentials not configured.")
        return False
        
    sender_email = SMTP_EMAIL
    receiver_email = target_email

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your CheckMate Password"
    msg["From"] = sender_email
    msg["To"] = receiver_email

    reset_link = f"http://localhost:5173/?reset_token={token}"

    text = f"Hi there!\n\nYou requested a password reset. Click this link to reset it:\n{reset_link}"
    html = f"""\
    <html>
      <body>
        <h2>Reset Your Password</h2>
        <p>Please click the button below to reset your CheckMate password:</p>
        <a href="{reset_link}" style="display:inline-block;padding:10px 20px;background-color:#4f46e5;color:white;text-decoration:none;border-radius:5px;">Reset Password</a>
        <p><br>If the button doesn't work, copy and paste this link:<br>{reset_link}</p>
        <p>If you didn't request this, you can safely ignore this email. This link will expire in 1 hour.</p>
      </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, SMTP_PASSWORD)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
