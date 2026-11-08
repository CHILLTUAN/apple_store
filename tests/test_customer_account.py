import unittest
from unittest.mock import patch

import app as store_app
import database.notification_repository as notification_repository


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
        self.description = []
        self.rows = []

    def execute(self, query, params=()):
        self.executions.append((query, params))
        self.row = None
        self.rowcount = 0
        self.description = []
        self.rows = []
        if "SELECT user_id, full_name, phone, email, address, username" in query:
            if params[0] == CUSTOMER[0]:
                self.row = CUSTOMER
        elif "COUNT(*)" in query and "FROM CustomerNotifications" in query:
            self.row = (2,)
        elif "DELETE FROM CustomerNotifications" in query:
            self.rowcount = 1 if params == (91, CUSTOMER[0]) else 0
        elif "FROM CustomerNotifications" in query:
            self.description = [
                (name,)
                for name in (
                    "notification_id",
                    "order_id",
                    "notification_type",
                    "title",
                    "message",
                    "is_read",
                    "created_at",
                )
            ]
            self.rows = [
                (
                    91,
                    73,
                    "order_approved",
                    "Đơn hàng đã được duyệt",
                    "Đơn hàng #73 đã được duyệt và đang được chuẩn bị.",
                    False,
                    "2026-11-08 10:00",
                )
            ]
        elif "UPDATE CustomerNotifications" in query:
            self.rowcount = 1
        elif "SELECT user_id FROM Users" in query and "email = ?" in query:
            self.row = None
        elif "FROM Orders" in query and "WHERE o.user_id = ?" in query:
            self.description = [
                (name,)
                for name in (
                    "order_id",
                    "order_date",
                    "total_amount",
                    "order_status",
                    "payment_status",
                    "shipping_address",
                    "product_id",
                    "product_name",
                    "color",
                    "ram",
                    "rom",
                    "charger_power",
                    "quantity",
                    "unit_price",
                    "engraving_text",
                    "line_total",
                )
            ]
            self.rows = [
                (
                    73,
                    None,
                    1499,
                    "Đang giao",
                    "Chưa thanh toán",
                    "Test address",
                    12,
                    "iPhone Test",
                    "Đen",
                    "8GB",
                    "256GB",
                    None,
                    2,
                    1499,
                    "For Linh",
                    2998,
                )
            ]
        elif "UPDATE Users" in query:
            self.rowcount = 1

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


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
        self.notification_connection_patch = patch.object(
            notification_repository, "get_connection", return_value=self.connection
        )
        self.categories_patch.start()
        self.connection_patch.start()
        self.notification_connection_patch.start()
        self.addCleanup(self.categories_patch.stop)
        self.addCleanup(self.connection_patch.stop)
        self.addCleanup(self.notification_connection_patch.stop)
        with self.client.session_transaction() as current_session:
            current_session["customer_user_id"] = CUSTOMER[0]
            current_session["csrf_token"] = "account-test-token"

    def test_user_icon_opens_profile_with_edit_and_logout_actions(self):
        with patch.object(store_app, "get_home_products", return_value=[]):
            home = self.client.get("/")
        self.assertIn(b'href="/account"', home.data)
        self.assertIn(b'href="/account/notifications"', home.data)
        self.assertRegex(
            home.get_data(as_text=True),
            r'class="notification-count"[^>]*>\s*2\s*</span>',
        )

        profile = self.client.get("/account")
        self.assertEqual(profile.status_code, 200)
        self.assertIn(b"Test Customer", profile.data)
        self.assertIn(b"CUSTOMER", profile.data)
        self.assertIn("Thay đổi thông tin cá nhân".encode(), profile.data)
        self.assertIn("Đăng xuất".encode(), profile.data)
        self.assertIn(b'action="/logout"', profile.data)
        self.assertIn(b'href="/account/orders"', profile.data)

    def test_customer_can_track_their_orders(self):
        response = self.client.get("/account/orders")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Đơn hàng #73".encode(), response.data)
        self.assertIn("Đang giao".encode(), response.data)
        self.assertIn("1.499 ₫".encode(), response.data)
        self.assertIn("iPhone Test".encode(), response.data)
        self.assertIn("RAM 8GB".encode(), response.data)
        self.assertIn("For Linh".encode(), response.data)
        self.assertIn("2.998 ₫".encode(), response.data)
        query, params = next(
            (query, params)
            for query, params in reversed(self.connection.test_cursor.executions)
            if "WHERE o.user_id = ?" in query
        )
        self.assertIn("WHERE o.user_id = ?", query)
        self.assertEqual(params, (CUSTOMER[0],))

    def test_customer_can_view_and_mark_notifications_read(self):
        response = self.client.get("/account/notifications")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Đơn hàng đã được duyệt".encode(), response.data)
        self.assertIn("Đơn hàng #73 đã được duyệt".encode(), response.data)
        self.assertIn(b'action="/account/notifications/read"', response.data)
        self.assertIn(
            b'action="/account/notifications/91/delete"',
            response.data,
        )

        response = self.client.post(
            "/account/notifications/read",
            data={"csrf_token": "account-test-token"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/account/notifications")
        query, params = self.connection.test_cursor.executions[-1]
        self.assertIn("UPDATE CustomerNotifications", query)
        self.assertEqual(params, (CUSTOMER[0],))

    def test_customer_can_delete_their_notification(self):
        response = self.client.post(
            "/account/notifications/91/delete",
            data={"csrf_token": "account-test-token"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/account/notifications")
        query, params = self.connection.test_cursor.executions[-1]
        self.assertIn("DELETE FROM CustomerNotifications", query)
        self.assertIn("notification_id = ? AND user_id = ?", query)
        self.assertEqual(params, (91, CUSTOMER[0]))

    def test_customer_cannot_delete_another_customers_notification(self):
        response = self.client.post(
            "/account/notifications/92/delete",
            data={"csrf_token": "account-test-token"},
        )

        self.assertEqual(response.status_code, 404)
        query, params = self.connection.test_cursor.executions[-1]
        self.assertIn("DELETE FROM CustomerNotifications", query)
        self.assertEqual(params, (92, CUSTOMER[0]))

    def test_notifications_require_customer_login(self):
        with self.client.session_transaction() as current_session:
            current_session.pop("customer_user_id")

        response = self.client.get("/account/notifications")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

    def test_order_tracking_requires_customer_login(self):
        with self.client.session_transaction() as current_session:
            current_session.pop("customer_user_id")

        response = self.client.get("/account/orders")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")

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

    def test_page_refresh_keeps_customer_signed_in(self):
        with patch.object(store_app, "get_home_products", return_value=[]):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"logout-on-close.js", response.data)
        with self.client.session_transaction() as current_session:
            self.assertEqual(current_session["customer_user_id"], CUSTOMER[0])
            self.assertFalse(current_session.permanent)

    def test_account_page_requires_customer_login(self):
        with self.client.session_transaction() as current_session:
            current_session.pop("customer_user_id")

        response = self.client.get("/account")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/login")


if __name__ == "__main__":
    unittest.main()
