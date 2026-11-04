import unittest
from unittest.mock import patch

import app as store_app


CUSTOMER = (
    42,
    "Test Customer",
    "0912345678",
    "customer@example.com",
    "Test address",
    "CUSTOMER",
)


class CustomerAccountCursor:
    def __init__(self):
        self.row = None
        self.rowcount = 0
        self.executions = []

    def execute(self, query, params=()):
        self.executions.append((query, params))
        self.row = None
        self.rowcount = 0
        if "SELECT user_id, full_name, phone, email, address, username" in query:
            if params[0] == CUSTOMER[0]:
                self.row = CUSTOMER
        elif "SELECT user_id FROM Users" in query and "email = ?" in query:
            self.row = None
        elif "UPDATE Users" in query:
            self.rowcount = 1

    def fetchone(self):
        return self.row


class CustomerAccountConnection:
    def __init__(self):
        self.test_cursor = CustomerAccountCursor()
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


class CustomerAccountTests(unittest.TestCase):
    def setUp(self):
        store_app.app.config.update(TESTING=True, SECRET_KEY="account-test-secret")
        self.client = store_app.app.test_client()
        self.connection = CustomerAccountConnection()
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
        with self.client.session_transaction() as current_session:
            current_session["customer_user_id"] = CUSTOMER[0]
            current_session["csrf_token"] = "account-test-token"

    def test_user_icon_opens_profile_with_edit_and_logout_actions(self):
        with patch.object(store_app, "get_home_products", return_value=[]):
            home = self.client.get("/")
        self.assertIn(b'href="/account"', home.data)

        profile = self.client.get("/account")
        self.assertEqual(profile.status_code, 200)
        self.assertIn(b"Test Customer", profile.data)
        self.assertIn(b"CUSTOMER", profile.data)
        self.assertIn("Thay đổi thông tin cá nhân".encode(), profile.data)
        self.assertIn("Đăng xuất".encode(), profile.data)
        self.assertIn(b'action="/logout"', profile.data)

    def test_customer_can_update_personal_information(self):
        response = self.client.post(
            "/account/edit",
            data={
                "csrf_token": "account-test-token",
                "full_name": "Updated Customer",
                "phone": "0987654321",
                "email": "updated@example.com",
                "address": "New address",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/account")
        self.assertTrue(self.connection.committed)
        update = next(
            params
            for query, params in self.connection.test_cursor.executions
            if "UPDATE Users" in query
        )
        self.assertEqual(
            update,
            (
                "Updated Customer",
                "0987654321",
                "updated@example.com",
                "New address",
                CUSTOMER[0],
            ),
        )

    def test_profile_edit_requires_csrf_token(self):
        response = self.client.post(
            "/account/edit",
            data={"full_name": "Updated Customer"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.connection.test_cursor.executions)

    def test_customer_can_log_out_and_receives_notification(self):
        response = self.client.post(
            "/logout",
            data={"csrf_token": "account-test-token"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")
        with self.client.session_transaction() as current_session:
            self.assertNotIn("customer_user_id", current_session)

        login_page = self.client.get("/login")
        self.assertIn("Bạn đã đăng xuất.".encode(), login_page.data)

    def test_account_page_requires_customer_login(self):
        with self.client.session_transaction() as current_session:
            current_session.pop("customer_user_id")

        response = self.client.get("/account")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")


if __name__ == "__main__":
    unittest.main()
