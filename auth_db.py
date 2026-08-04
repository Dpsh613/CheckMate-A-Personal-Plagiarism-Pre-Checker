import bcrypt
import hashlib
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone


DB_FILE = "users.sqlite"
MIN_PASSWORD_BYTES = 12
MAX_PASSWORD_BYTES = 72
BCRYPT_ROUNDS = 12


def _utcnow():
    return datetime.now(timezone.utc)


def _token_hash(token: str) -> str:
    """Store only a digest of one-time tokens, never the token itself."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _password_bytes(password: str):
    password_bytes = password.encode("utf-8")
    if len(password_bytes) < MIN_PASSWORD_BYTES:
        return None, f"Password must be at least {MIN_PASSWORD_BYTES} bytes long."
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        return None, f"Password must be at most {MAX_PASSWORD_BYTES} bytes long."
    return password_bytes, None


def _connect():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def _database():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _token_schema_is_legacy(conn, table_name: str) -> bool:
    columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}
    return bool(columns) and "token_hash" not in columns


def init_db():
    with _database() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_verified BOOLEAN NOT NULL DEFAULT 0
            )
            """
        )

        # Earlier versions stored reset/verification tokens in plaintext. Removing
        # those rows invalidates any outstanding links, which is the safe migration.
        for table in ("verification_tokens", "password_reset_tokens"):
            if _token_schema_is_legacy(conn, table):
                conn.execute(f"DROP TABLE {table}")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS verification_tokens (
                token_hash TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token_hash TEXT PRIMARY KEY,
                email TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )


def get_user_by_email(email: str):
    email = email.strip().lower()
    with _database() as conn:
        user = conn.execute(
            "SELECT id, email, password_hash, is_verified FROM users WHERE email = ?", (email,)
        ).fetchone()
    if user:
        return {"id": user[0], "email": user[1], "password_hash": user[2], "is_verified": bool(user[3])}
    return None


def delete_user_by_email(email: str):
    email = email.strip().lower()
    with _database() as conn:
        conn.execute("DELETE FROM users WHERE email = ?", (email,))


def create_user(email: str, password: str, is_verified: bool = False):
    email = email.strip().lower()
    password_bytes, error = _password_bytes(password)
    if error:
        return False, error

    existing = get_user_by_email(email)
    if existing:
        if existing["is_verified"]:
            return False, "Email already exists"
        delete_user_by_email(email)

    password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")
    try:
        with _database() as conn:
            conn.execute(
                "INSERT INTO users (email, password_hash, is_verified) VALUES (?, ?, ?)",
                (email, password_hash, 1 if is_verified else 0),
            )
        return True, "User created successfully"
    except sqlite3.IntegrityError:
        return False, "Email already exists"


def verify_password(plain_password: str, hashed_password: str):
    password_bytes, error = _password_bytes(plain_password)
    if error:
        return False
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def create_verification_token(email: str):
    token = secrets.token_urlsafe(32)
    expires_at = (_utcnow() + timedelta(hours=1)).isoformat()
    with _database() as conn:
        conn.execute("DELETE FROM verification_tokens WHERE email = ?", (email.strip().lower(),))
        conn.execute(
            "INSERT INTO verification_tokens (token_hash, email, expires_at) VALUES (?, ?, ?)",
            (_token_hash(token), email.strip().lower(), expires_at),
        )
    return token


def verify_user_token(token: str):
    with _database() as conn:
        row = conn.execute(
            "SELECT email, expires_at FROM verification_tokens WHERE token_hash = ?", (_token_hash(token),)
        ).fetchone()
        if not row:
            return False, "Invalid token"

        email, expires_at_str = row
        conn.execute("DELETE FROM verification_tokens WHERE token_hash = ?", (_token_hash(token),))
        if _utcnow() > datetime.fromisoformat(expires_at_str):
            return False, "Token expired"

        conn.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (email,))
    return True, "Email successfully verified"


def create_password_reset_token(email: str):
    token = secrets.token_urlsafe(32)
    expires_at = (_utcnow() + timedelta(hours=1)).isoformat()
    with _database() as conn:
        conn.execute("DELETE FROM password_reset_tokens WHERE email = ?", (email.strip().lower(),))
        conn.execute(
            "INSERT INTO password_reset_tokens (token_hash, email, expires_at) VALUES (?, ?, ?)",
            (_token_hash(token), email.strip().lower(), expires_at),
        )
    return token


def reset_password_with_token(token: str, new_password: str):
    password_bytes, error = _password_bytes(new_password)
    if error:
        return False, error

    with _database() as conn:
        row = conn.execute(
            "SELECT email, expires_at FROM password_reset_tokens WHERE token_hash = ?", (_token_hash(token),)
        ).fetchone()
        if not row:
            return False, "Invalid token"

        email, expires_at_str = row
        # Consume a reset token before changing the password, including expired tokens.
        conn.execute("DELETE FROM password_reset_tokens WHERE token_hash = ?", (_token_hash(token),))
        if _utcnow() > datetime.fromisoformat(expires_at_str):
            return False, "Token expired"

        password_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("utf-8")
        conn.execute("UPDATE users SET password_hash = ? WHERE email = ?", (password_hash, email))
    return True, "Password successfully reset"


init_db()
