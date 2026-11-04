import unittest
from unittest.mock import patch

from werkzeug.security import check_password_hash

import app as store_app


class RegistrationCursor:
    def __init__(self):
        self.row = None
        self.executions = []

    def execute(self, query, params=()):
        self.executions.append((query, params))
        self.row = None

    def fetchone(self):
        return self.row


class RegistrationConnection:
    def __init__(self):
        self.test_cursor = RegistrationCursor()
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self.test_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class CustomerRegistrationTests(unittest.TestCase):
    def setUp(self):
        store_app.app.config.update(TESTING=True, SECRET_KEY="registration-test-secret")
        self.client = store_app.app.test_client()
        self.connection = RegistrationConnection()
        self.categories_patch = patch.object(
            store_app, "get_categories", return_value=[]
        )
        self.connection_patch = patch.object(
            store_app, "get_connection", return_value=self.connection
        )
        self.categories_patch.start()
        self.connection_patch.start()
        self.addCleanup(self.categories_patch.stop)
        self.addCleanup(self.connection_patch.stop)
        self.client.get("/register")
        with self.client.session_transaction() as current_session:
            self.csrf_token = current_session["csrf_token"]

    def test_registration_creates_customer_with_hashed_password(self):
        response = self.client.post(
            "/register",
            data={
                "csrf_token": self.csrf_token,
                "full_name": "Test Customer",
                "phone": "0912345678",
                "email": "customer@example.com",
                "address": "Test address",
                "username": "CUSTOMER",
                "password": "customer-password",
                "confirm_password": "customer-password",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")
        self.assertTrue(self.connection.committed)
        insert_query, insert = next(
            (query, params)
            for query, params in self.connection.test_cursor.executions
            if "INSERT INTO Users" in query
        )
        self.assertEqual(
            insert[:5],
            (
                "Test Customer",
                "0912345678",
                "customer@example.com",
                "Test address",
                "CUSTOMER",
            ),
        )
        self.assertTrue(check_password_hash(insert[5], "customer-password"))
        self.assertIn("VALUES (?, ?, ?, ?, ?, ?, 3, 1)", insert_query)
        self.assertFalse(
            any(
                "UPDATE Users" in query
                for query, _ in self.connection.test_cursor.executions
            )
        )

        login_page = self.client.get("/login")
        self.assertIn("Đăng ký thành công".encode(), login_page.data)

    def test_registration_rejects_mismatched_passwords_without_database_write(self):
        with patch.object(
            store_app,
            "get_connection",
            side_effect=AssertionError("Invalid registration must not access the database."),
        ):
            response = self.client.post(
                "/register",
                data={
                    "csrf_token": self.csrf_token,
                    "full_name": "Test Customer",
                    "username": "CUSTOMER",
                    "password": "customer-password",
                    "confirm_password": "different-password",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Vui lòng kiểm tra lại thông tin đăng ký".encode(), response.data)

    def test_registration_requires_csrf_token(self):
        response = self.client.post(
            "/register",
            data={
                "full_name": "Test Customer",
                "username": "CUSTOMER",
                "password": "customer-password",
                "confirm_password": "customer-password",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.connection.test_cursor.executions)


if __name__ == "__main__":
    unittest.main()
