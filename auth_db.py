import sqlite3
import bcrypt
import os
import secrets
from datetime import datetime, timedelta

DB_FILE = "users.sqlite"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_verified BOOLEAN NOT NULL DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS verification_tokens (
            token TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            expires_at DATETIME NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            token TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            expires_at DATETIME NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def get_user_by_email(email: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, email, password_hash, is_verified FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    if user:
        return {"id": user[0], "email": user[1], "password_hash": user[2], "is_verified": bool(user[3])}
    return None

def create_user(email: str, password: str):
    user = get_user_by_email(email)
    if user:
        return False, "Email already exists"
    
    password_bytes = password.encode('utf-8')
    # Prevent the 72 byte limit error by truncating or just passing it
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password_hash, is_verified) VALUES (?, ?, 1)", (email, password_hash))
        conn.commit()
        return True, "User created successfully"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def verify_password(plain_password, hashed_password):
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))

def create_verification_token(email: str):
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO verification_tokens (token, email, expires_at) VALUES (?, ?, ?)", (token, email, expires_at))
    conn.commit()
    conn.close()
    
    return token

def verify_user_token(token: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT email, expires_at FROM verification_tokens WHERE token = ?", (token,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return False, "Invalid token"
        
    email, expires_at_str = row
    expires_at = datetime.fromisoformat(expires_at_str)
    
    if datetime.utcnow() > expires_at:
        c.execute("DELETE FROM verification_tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return False, "Token expired"
        
    c.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (email,))
    c.execute("DELETE FROM verification_tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    
    return True, "Email successfully verified"

def create_password_reset_token(email: str):
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Remove existing tokens for this email
    c.execute("DELETE FROM password_reset_tokens WHERE email = ?", (email,))
    c.execute("INSERT INTO password_reset_tokens (token, email, expires_at) VALUES (?, ?, ?)", (token, email, expires_at))
    conn.commit()
    conn.close()
    
    return token

def reset_password_with_token(token: str, new_password: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT email, expires_at FROM password_reset_tokens WHERE token = ?", (token,))
    row = c.fetchone()
    
    if not row:
        conn.close()
        return False, "Invalid token"
        
    email, expires_at_str = row
    expires_at = datetime.fromisoformat(expires_at_str)
    
    c.execute("DELETE FROM password_reset_tokens WHERE token = ?", (token,))
    
    if datetime.utcnow() > expires_at:
        conn.commit()
        conn.close()
        return False, "Token expired"
        
    password_bytes = new_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    c.execute("UPDATE users SET password_hash = ? WHERE email = ?", (password_hash, email))
    conn.commit()
    conn.close()
    
    return True, "Password successfully reset"

# Initialize DB on load
init_db()
