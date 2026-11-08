import unittest
from unittest.mock import patch

from werkzeug.security import check_password_hash, generate_password_hash

import app as store_app
from routes import admin as admin_routes


class FakeCursor:
    executed_queries = []

    def __init__(self):
        self.row = None
        self.rows = []
        self.description = []
        self.rowcount = 0

    def execute(self, query, params=()):
        self.executed_queries.append(query)
        self.row = None
        self.rows = []
        self.description = []

        if "SELECT user_id, full_name, password_hash, role, is_active" in query:
            user = USERS_BY_USERNAME.get(params[0])
            if user:
                self.row = (user[0], user[1], user[2], user[3], user[4])
        elif "SELECT user_id, full_name, username, role, is_active" in query:
            self.row = USERS_BY_ID.get(params[0])
        elif "AS customers" in query:
            self.description = [(name,) for name in (
                "customers",
                "revenue_today",
                "revenue_month",
                "revenue_year",
            )]
            self.rows = [(6, 100000, 200000, 300000)]
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


class UserActionCursor:
    executions = []
    user_to_delete = (2, 3, True, "customer")
    active_order_count = 0
    cancelled_order_count = 0
    inserted_user = None

    def __init__(self):
        self.row = None
        self.rows = []
        self.description = []

    def execute(self, query, params=()):
        self.executions.append((query, params))
        self.row = None
        self.rows = []
        self.description = []
        if "SELECT user_id, full_name, username, role, is_active" in query:
            self.row = USERS_BY_ID.get(params[0])
        elif "SELECT user_id, role, is_active FROM Users" in query:
            self.row = (2, 3, True)
        elif "SELECT user_id, role, is_active, username FROM Users" in query:
            self.row = self.user_to_delete
        elif "SELECT user_id, full_name, phone, email, username, role" in query:
            self.description = [
                (name,)
                for name in (
                    "user_id",
                    "full_name",
                    "phone",
                    "email",
                    "username",
                    "role",
                    "is_active",
                    "created_at",
                )
            ]
            self.rows = [(2, "Store Customer", None, None, "customer", 3, True, None)]
        elif "WHERE username = ? OR (? IS NOT NULL AND email = ?)" in query:
            if params[0] == "taken" or params[2] == "taken@example.com":
                self.row = (99,)
        elif "INSERT INTO Users" in query:
            type(self).inserted_user = params
        elif "SELECT COUNT(*) FROM Users" in query:
            self.row = (1,)
        elif "SELECT COUNT(*) FROM Orders" in query:
            self.row = (
                self.cancelled_order_count
                if "order_status = N'Đã hủy'" in query
                else self.active_order_count,
            )

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class UserActionConnection:
    def cursor(self):
        return UserActionCursor()

    def commit(self):
        pass

    def rollback(self):
        pass

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
        FakeCursor.executed_queries = []
        UserActionCursor.executions = []
        UserActionCursor.user_to_delete = (2, 3, True, "customer")
        UserActionCursor.active_order_count = 0
        UserActionCursor.cancelled_order_count = 0
        UserActionCursor.inserted_user = None
        store_app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = store_app.app.test_client()
        self.categories_patch = patch.object(store_app, "get_categories", return_value=[])
        self.connection_patch = patch.object(
            store_app, "get_connection", side_effect=lambda: FakeConnection()
        )
        self.admin_connection_patch = patch.object(
            admin_routes, "get_connection", side_effect=lambda: FakeConnection()
        )
        self.admin_products_patch = patch.object(
            admin_routes, "get_admin_products", return_value=[]
        )
        self.categories_patch.start()
        self.connection_patch.start()
        self.admin_connection_patch.start()
        self.admin_products_patch.start()
        self.addCleanup(self.categories_patch.stop)
        self.addCleanup(self.connection_patch.stop)
        self.addCleanup(self.admin_connection_patch.stop)
        self.addCleanup(self.admin_products_patch.stop)

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
        response = self.client.post(
            "/login",
            data={
                "username": "admin",
                "password": "correct-horse-battery",
                "csrf_token": self._csrf_token(),
                "remember_me": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/admin/")
        session_cookie = response.headers["Set-Cookie"]
        self.assertNotIn("Expires=", session_cookie)
        self.assertNotIn("Max-Age=", session_cookie)
        with self.client.session_transaction() as current_session:
            self.assertEqual(current_session["cart"], {"20": 1})
            self.assertFalse(current_session.permanent)

        dashboard = self.client.get(response.headers["Location"])
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Doanh thu h\xc3\xb4m nay", dashboard.data)
        self.assertIn(b"Store Admin", dashboard.data)
        self.assertFalse(any("SELECT TOP 8" in query for query in FakeCursor.executed_queries))
        self.assertNotIn("Đơn hàng gần đây".encode(), dashboard.data)

    def test_customer_login_does_not_grant_admin_access(self):
        response = self.client.post(
            "/login",
            data={
                "username": "customer",
                "password": "customer-password",
                "csrf_token": self._csrf_token(),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        with self.client.session_transaction() as current_session:
            self.assertIn("customer_user_id", current_session)
            self.assertNotIn("admin_user_id", current_session)

        admin_page = self.client.get("/admin/")
        self.assertEqual(admin_page.status_code, 302)
        self.assertTrue(admin_page.headers["Location"].startswith("/login?next="))

    def test_admin_pages_require_a_signed_in_account(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/login?next="))

    def test_user_management_page_renders(self):
        self._login_admin()
        with patch.object(
            admin_routes, "get_connection", side_effect=UserActionConnection
        ):
            response = self.client.get("/admin/users")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Th\xc3\xaam ng\xc6\xb0\xe1\xbb\x9di d\xc3\xb9ng", response.data)
        self.assertIn(b"Ph\xc3\xa2n quy\xe1\xbb\x81n", response.data)
        self.assertIn(b"X\xc3\xb3a", response.data)

    def test_admin_can_add_user_with_valid_details(self):
        self._login_admin()
        csrf_token = self._csrf_token()

        with patch.object(
            admin_routes, "get_connection", side_effect=UserActionConnection
        ):
            response = self.client.post(
                "/admin/users/new",
                data={
                    "csrf_token": csrf_token,
                    "full_name": "New Customer",
                    "username": "new_customer",
                    "password": "secure-password",
                    "email": "new@example.com",
                    "phone": "0912345678",
                    "address": "Test address",
                    "role": "3",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/admin/users")
        self.assertIsNotNone(UserActionCursor.inserted_user)
        self.assertEqual(UserActionCursor.inserted_user[:5], (
            "New Customer",
            "0912345678",
            "new@example.com",
            "Test address",
            "new_customer",
        ))
        self.assertTrue(
            check_password_hash(UserActionCursor.inserted_user[5], "secure-password")
        )
        self.assertEqual(UserActionCursor.inserted_user[6], 3)

    def test_admin_add_user_rejects_duplicate_username_or_email(self):
        self._login_admin()
        csrf_token = self._csrf_token()

        with patch.object(
            admin_routes, "get_connection", side_effect=UserActionConnection
        ):
            response = self.client.post(
                "/admin/users/new",
                data={
                    "csrf_token": csrf_token,
                    "full_name": "New Customer",
                    "username": "available",
                    "password": "secure-password",
                    "email": "taken@example.com",
                    "role": "3",
                },
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Tên đăng nhập hoặc email đã được sử dụng.".encode(),
            response.data,
        )
        self.assertIsNone(UserActionCursor.inserted_user)

    def test_add_user_form_has_password_visibility_toggle(self):
        self._login_admin()

        with patch.object(
            admin_routes, "get_connection", side_effect=UserActionConnection
        ):
            response = self.client.get("/admin/users/new")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'data-password-toggle="user-password"', response.data)
        self.assertIn(b'aria-label="Hi\xe1\xbb\x87n m\xe1\xba\xadt kh\xe1\xba\xa9u"', response.data)

    def test_user_can_be_assigned_a_role(self):
        self._login_admin()
        csrf_token = self._csrf_token()
        with patch.object(
            admin_routes, "get_connection", side_effect=UserActionConnection
        ):
            response = self.client.post(
                "/admin/users/2/permissions",
                data={"csrf_token": csrf_token, "role": "2"},
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            any("UPDATE Users SET role = ?" in query for query, _ in UserActionCursor.executions)
        )

    def test_user_without_orders_can_be_deleted(self):
        self._login_admin()
        csrf_token = self._csrf_token()
        with patch.object(
            admin_routes, "get_connection", side_effect=UserActionConnection
        ):
            response = self.client.post(
                "/admin/users/2/delete",
                data={"csrf_token": csrf_token},
            )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            any("DELETE FROM Users" in query for query, _ in UserActionCursor.executions)
        )

    def test_guest_with_only_cancelled_orders_is_deleted_with_order_history(self):
        UserActionCursor.user_to_delete = (2, 3, True, "guest_0123456789")
        UserActionCursor.cancelled_order_count = 2
        self._login_admin()
        csrf_token = self._csrf_token()

        with patch.object(
            admin_routes, "get_connection", side_effect=UserActionConnection
        ):
            response = self.client.post(
                "/admin/users/2/delete",
                data={"csrf_token": csrf_token},
            )

        self.assertEqual(response.status_code, 302)
        executed_queries = [query for query, _ in UserActionCursor.executions]
        self.assertTrue(any("DELETE details" in query for query in executed_queries))
        self.assertTrue(
            any("DELETE FROM Orders WHERE user_id" in query for query in executed_queries)
        )
        self.assertTrue(any("DELETE FROM Users" in query for query in executed_queries))

    def test_guest_with_active_orders_cannot_be_deleted(self):
        UserActionCursor.user_to_delete = (2, 3, True, "guest_0123456789")
        UserActionCursor.active_order_count = 1
        self._login_admin()
        csrf_token = self._csrf_token()

        with patch.object(
            admin_routes, "get_connection", side_effect=UserActionConnection
        ):
            response = self.client.post(
                "/admin/users/2/delete",
                data={"csrf_token": csrf_token},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            b"Kh\xc3\xb4ng th\xe1\xbb\x83 x\xc3\xb3a ng\xc6\xb0\xe1\xbb\x9di d\xc3\xb9ng "
            b"\xc4\x91\xc3\xa3 c\xc3\xb3 \xc4\x91\xc6\xa1n h\xc3\xa0ng.",
            response.data,
        )
        self.assertFalse(
            any("DELETE FROM Users" in query for query, _ in UserActionCursor.executions)
        )

    def test_login_requires_csrf_token(self):
        response = self.client.post(
            "/login",
            data={"username": "admin", "password": "correct-horse-battery"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
