import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

import app as store_app
from routes import admin as admin_routes


class FakeCursor:
    def __init__(self):
        self.row = None
        self.rows = []
        self.description = []
        self.rowcount = 0

    def execute(self, query, params=()):
        self.row = None
        self.rows = []
        self.description = []

        if "SELECT user_id, full_name, password_hash, role, is_active" in query:
            user = USERS_BY_USERNAME.get(params[0])
            if user:
                self.row = (user[0], user[1], user[2], user[3], user[4])
        elif "SELECT user_id, full_name, username, role, is_active" in query:
            self.row = USERS_BY_ID.get(params[0])
        elif "AS total_orders" in query:
            self.description = [(name,) for name in (
                "total_orders",
                "customers",
                "pending_orders",
                "revenue_today",
                "revenue_month",
                "revenue_year",
            )]
            self.rows = [(5, 6, 3, 1, 100000, 200000, 300000)]
        elif "SELECT TOP 8" in query:
            self.description = [(name,) for name in (
                "order_id",
                "full_name",
                "order_date",
                "total_amount",
                "order_status",
                "payment_method",
            )]
        elif "SUM(total_amount)" in query:
            self.description = [(name,) for name in ("month_start", "revenue")]

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class FakeConnection:
    def cursor(self):
        return FakeCursor()

    def close(self):
        pass


ADMIN_PASSWORD_HASH = generate_password_hash("correct-horse-battery")
CUSTOMER_PASSWORD_HASH = generate_password_hash("customer-password")
USERS_BY_USERNAME = {
    "admin": (1, "Store Admin", ADMIN_PASSWORD_HASH, 1, True),
    "customer": (2, "Store Customer", CUSTOMER_PASSWORD_HASH, 3, True),
}
USERS_BY_ID = {
    1: (1, "Store Admin", "admin", 1, True),
    2: (2, "Store Customer", "customer", 3, True),
}


class AdminAuthenticationTests(unittest.TestCase):
    def setUp(self):
        store_app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = store_app.app.test_client()
        self.categories_patch = patch.object(store_app, "get_categories", return_value=[])
        self.connection_patch = patch.object(
            store_app, "get_connection", side_effect=lambda: FakeConnection()
        )
        self.admin_connection_patch = patch.object(
            admin_routes, "get_connection", side_effect=lambda: FakeConnection()
        )
        self.home_products_patch = patch.object(admin_routes, "get_home_products", return_value=[])
        self.categories_patch.start()
        self.connection_patch.start()
        self.admin_connection_patch.start()
        self.home_products_patch.start()
        self.addCleanup(self.categories_patch.stop)
        self.addCleanup(self.connection_patch.stop)
        self.addCleanup(self.admin_connection_patch.stop)
        self.addCleanup(self.home_products_patch.stop)

    def _csrf_token(self):
        self.client.get("/login")
        with self.client.session_transaction() as current_session:
            return current_session["csrf_token"]

    def _login_admin(self):
        return self.client.post(
            "/login",
            data={
                "username": "admin",
                "password": "correct-horse-battery",
                "csrf_token": self._csrf_token(),
            },
        )

    def test_admin_login_redirects_to_dashboard_and_renders(self):
        with self.client.session_transaction() as current_session:
            current_session["cart"] = {"20": 1}
        response = self._login_admin()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/admin/")
        with self.client.session_transaction() as current_session:
            self.assertEqual(current_session["cart"], {"20": 1})

        dashboard = self.client.get(response.headers["Location"])
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Doanh thu h\xc3\xb4m nay", dashboard.data)
        self.assertIn(b"Store Admin", dashboard.data)

    def test_customer_account_cannot_log_in_to_admin(self):
        response = self.client.post(
            "/login",
            data={
                "username": "customer",
                "password": "customer-password",
                "csrf_token": self._csrf_token(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"kh\xc3\xb4ng c\xc3\xb3 quy\xe1\xbb\x81n qu\xe1\xba\xa3n tr\xe1\xbb\x8b", response.data)

    def test_admin_pages_require_a_signed_in_account(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/login?next="))

    def test_user_management_page_renders(self):
        self._login_admin()
        response = self.client.get("/admin/users")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Th\xc3\xaam ng\xc6\xb0\xe1\xbb\x9di d\xc3\xb9ng", response.data)

    def test_login_requires_csrf_token(self):
        response = self.client.post(
            "/login",
            data={"username": "admin", "password": "correct-horse-battery"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
