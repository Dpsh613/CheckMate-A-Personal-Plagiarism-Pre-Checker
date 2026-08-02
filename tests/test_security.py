import os
import sqlite3
import tempfile
import unittest

import auth_db
from arxiv_manager import _is_valid_arxiv_pdf_url


class AuthSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_file = auth_db.DB_FILE
        auth_db.DB_FILE = os.path.join(self.temp_dir.name, "users.sqlite")
        auth_db.init_db()

    def tearDown(self):
        auth_db.DB_FILE = self.original_db_file
        self.temp_dir.cleanup()

    def test_new_users_require_verification(self):
        success, _ = auth_db.create_user("student@example.com", "correct-horse-battery-staple")
        self.assertTrue(success)
        self.assertFalse(auth_db.get_user_by_email("student@example.com")["is_verified"])

    def test_password_limits_are_enforced_without_truncation(self):
        self.assertFalse(auth_db.create_user("short@example.com", "short")[0])
        self.assertFalse(auth_db.create_user("long@example.com", "a" * 73)[0])

    def test_one_time_tokens_are_hashed_and_consumed(self):
        auth_db.create_user("student@example.com", "correct-horse-battery-staple")
        token = auth_db.create_password_reset_token("student@example.com")
        conn = sqlite3.connect(auth_db.DB_FILE)
        try:
            stored_hash = conn.execute("SELECT token_hash FROM password_reset_tokens").fetchone()[0]
        finally:
            conn.close()
        self.assertNotEqual(token, stored_hash)
        self.assertTrue(auth_db.reset_password_with_token(token, "another-safe-password")[0])
        self.assertFalse(auth_db.reset_password_with_token(token, "another-safe-password")[0])


class ArxivUrlValidationTests(unittest.TestCase):
    def test_only_https_arxiv_pdf_urls_are_accepted(self):
        self.assertTrue(_is_valid_arxiv_pdf_url("https://arxiv.org/pdf/1234.5678"))
        self.assertFalse(_is_valid_arxiv_pdf_url("http://arxiv.org/pdf/1234.5678"))
        self.assertFalse(_is_valid_arxiv_pdf_url("https://arxiv.org.evil.example/pdf/1234.5678"))
        self.assertFalse(_is_valid_arxiv_pdf_url("https://arxiv.org/abs/1234.5678"))


class ApiSecurityIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Importing the application also verifies that its production dependencies
        # and route configuration can initialize successfully.
        from fastapi.testclient import TestClient
        import api

        cls.api = api
        cls.client_type = TestClient

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_file = auth_db.DB_FILE
        auth_db.DB_FILE = os.path.join(self.temp_dir.name, "users.sqlite")
        auth_db.init_db()
        self.client = self.client_type(self.api.app)

    def tearDown(self):
        self.client.close()
        auth_db.DB_FILE = self.original_db_file
        self.temp_dir.cleanup()

    def test_verified_login_requires_csrf_for_state_changes(self):
        password = "correct-horse-battery-staple"
        register = self.client.post("/register", json={"email": "student@example.com", "password": password})
        self.assertEqual(register.status_code, 200)
        self.assertFalse(auth_db.get_user_by_email("student@example.com")["is_verified"])

        token = auth_db.create_verification_token("student@example.com")
        self.assertTrue(auth_db.verify_user_token(token)[0])
        login = self.client.post("/login", json={"email": "student@example.com", "password": password})
        self.assertEqual(login.status_code, 200)
        self.assertIn("HttpOnly", login.headers["set-cookie"])
        self.assertEqual(self.client.post("/logout").status_code, 403)
        self.assertEqual(
            self.client.post("/logout", headers={"X-CSRF-Token": login.json()["csrf_token"]}).status_code,
            200,
        )
        self.assertEqual(login.headers["referrer-policy"], "no-referrer")
        self.assertIn("default-src 'none'", login.headers["content-security-policy"])


if __name__ == "__main__":
    unittest.main()
