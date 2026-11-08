import unittest
from datetime import datetime
from unittest.mock import patch

from werkzeug.security import generate_password_hash

import app as store_app
import database.notification_repository as notification_repository


CUSTOMER = (
    42,
    "Test Customer",
    generate_password_hash("customer-password"),
    3,
    True,
)


class CheckoutCursor:
    def __init__(self):
        self.row = None
        self.rows = []
        self.description = []
        self.rowcount = 0
        self.executions = []

    def execute(self, query, params=()):
        self.executions.append((query, params))
        self.row = None
        self.rows = []
        self.description = []
        self.rowcount = 0

        if "WITH (UPDLOCK, ROWLOCK)" in query:
            self.description = [
                ("product_id",),
                ("product_name",),
                ("color",),
                ("price",),
                ("stock_quantity",),
                ("reserved_quantity",),
            ]
            self.rows = [(10, "MacBook", "Bạc", 1000, 5, 0)]
        elif "COUNT(*)" in query and "FROM CustomerNotifications" in query:
            self.row = (0,)
        elif "SELECT user_id, full_name, password_hash, role, is_active" in query:
            if params[0] == "CUSTOMER":
                self.row = CUSTOMER
        elif "UPDATE Users" in query:
            self.rowcount = 1
        elif "INSERT INTO Orders" in query:
            self.row = (31,)
        elif "SELECT o.order_id, o.order_date, o.total_amount" in query:
            self.description = [
                (name,)
                for name in (
                    "order_id",
                    "order_date",
                    "total_amount",
                    "payment_method",
                    "payment_status",
                    "shipping_address",
                    "shipping_fee",
                    "order_status",
                    "note",
                    "full_name",
                    "phone",
                )
            ]
            self.rows = [
                (
                    31,
                    datetime(2026, 11, 3, 10, 30),
                    1000,
                    "Trả góp MoMo - 24 tháng",
                    "Chưa thanh toán",
                    "Test address",
                    0,
                    "Chờ duyệt",
                    "Customer note",
                    "Test Customer",
                    "0912345678",
                )
            ]
        elif "SELECT p.product_name, p.color, d.quantity, d.unit_price" in query:
            self.description = [
                ("product_name",),
                ("color",),
                ("quantity",),
                ("unit_price",),
                ("engraving_text",),
                ("line_total",),
            ]
            self.rows = [("MacBook", "Bạc", 1, 1000, "For Linh", 1000)]

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class CheckoutConnection:
    def __init__(self):
        self.test_cursor = CheckoutCursor()
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


class CustomerCheckoutTests(unittest.TestCase):
    def setUp(self):
        store_app.app.config.update(TESTING=True, SECRET_KEY="checkout-test-secret")
        self.client = store_app.app.test_client()
        self.connection = CheckoutConnection()
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
            current_session["csrf_token"] = "checkout-test-token"
            current_session["cart"] = {"10": 1}
            current_session["cart_engraving"] = {"10": "For Linh"}
            current_session["customer_user_id"] = CUSTOMER[0]

    def test_checkout_records_installment_trade_in_consultation_and_engraving(self):
        response = self.client.post(
            "/checkout",
            data={
                "csrf_token": "checkout-test-token",
                "full_name": "Test Customer",
                "phone": "0912345678",
                "shipping_address": "Test address",
                "payment_method": "momo_installment",
                "installment_months": "24",
                "trade_in_requested": "on",
                "trade_in_device": "Old phone, good condition",
                "consultation_requested": "on",
                "consultation_message": "Please advise on configuration",
                "note": "Deliver after 5 PM",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRegex(
            response.headers["Location"],
            r"^/orders/31/confirmation/[^/]+$",
        )
        self.assertTrue(self.connection.committed)
        self.assertFalse(self.connection.rolled_back)

        order_insert = next(
            params
            for query, params in self.connection.test_cursor.executions
            if "INSERT INTO Orders" in query
        )
        self.assertEqual(order_insert[2], "Trả góp MoMo - 24 tháng")
        self.assertEqual(order_insert[3], "Test address")
        self.assertIn("thu cũ đổi mới", order_insert[4])
        self.assertIn("tư vấn trực tuyến", order_insert[4])
        customer_update = next(
            params
            for query, params in self.connection.test_cursor.executions
            if "UPDATE Users" in query
        )
        self.assertEqual(
            customer_update,
            ("Test Customer", "0912345678", "Test address", CUSTOMER[0]),
        )

        detail_insert = next(
            params
            for query, params in self.connection.test_cursor.executions
            if "INSERT INTO OrderDetails" in query
        )
        self.assertEqual(detail_insert[-1], "For Linh")
        notification_insert = next(
            params
            for query, params in self.connection.test_cursor.executions
            if "INSERT INTO CustomerNotifications" in query
        )
        self.assertEqual(
            notification_insert,
            (
                CUSTOMER[0],
                31,
                "order_placed",
                "Đặt hàng thành công",
                "Đơn hàng #31 đã được tiếp nhận và đang chờ duyệt.",
            ),
        )
        self.assertEqual(order_insert[0], CUSTOMER[0])
        self.assertFalse(
            any(
                "INSERT INTO Users" in query
                for query, _ in self.connection.test_cursor.executions
            )
        )
        with self.client.session_transaction() as current_session:
            self.assertNotIn("cart", current_session)
            self.assertNotIn("cart_engraving", current_session)

        receipt = self.client.get(response.headers["Location"])
        self.assertEqual(receipt.status_code, 200)
        self.assertIn("Đặt hàng thành công".encode(), receipt.data)
        self.assertIn("Trả góp MoMo - 24 tháng".encode(), receipt.data)
        self.assertIn(b"window.print()", receipt.data)
        self.assertIn(b"window.location.replace", receipt.data)
        self.assertIn(b"Test address", receipt.data)

    def test_customer_login_redirects_back_to_product_and_confirms_success(self):
        response = self.client.post(
            "/login?next=/products/10",
            data={
                "username": "CUSTOMER",
                "password": "customer-password",
                "csrf_token": "checkout-test-token",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/products/10")
        with self.client.session_transaction() as current_session:
            self.assertEqual(current_session["customer_user_id"], CUSTOMER[0])
            self.assertNotIn("admin_user_id", current_session)

        with patch.object(store_app, "get_home_products", return_value=[]):
            home = self.client.get("/")
        self.assertIn("Đăng nhập thành công".encode(), home.data)

    def test_guest_add_to_cart_shows_login_action_without_accessing_products(self):
        with self.client.session_transaction() as current_session:
            current_session.pop("customer_user_id")

        with patch.object(
            store_app,
            "get_connection",
            side_effect=AssertionError("Guests must be blocked before product access."),
        ), patch.object(store_app, "get_home_products", return_value=[]):
            response = self.client.post(
                "/cart/items/10",
                data={"csrf_token": "checkout-test-token"},
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Để đặt hàng, vui lòng đăng nhập".encode(), response.data)
        self.assertIn(b'class="flash-action"', response.data)
        self.assertIn(">Đăng nhập</a>".encode(), response.data)

    def test_guest_checkout_is_redirected_to_login_prompt(self):
        with self.client.session_transaction() as current_session:
            current_session.pop("customer_user_id")

        with patch.object(
            store_app,
            "get_connection",
            side_effect=AssertionError("Guests must not reach checkout."),
        ):
            response = self.client.get("/checkout")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/")
        with self.client.session_transaction() as current_session:
            self.assertEqual(current_session["login_next"], "/checkout")

    def test_guest_cart_link_shows_login_action_and_returns_to_cart_after_login(self):
        with self.client.session_transaction() as current_session:
            current_session.pop("customer_user_id")

        with patch.object(
            store_app,
            "get_connection",
            side_effect=AssertionError("Guests must be blocked before cart access."),
        ), patch.object(store_app, "get_home_products", return_value=[]):
            response = self.client.get("/cart", follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("Để đặt hàng, vui lòng đăng nhập".encode(), response.data)
        self.assertIn(">Đăng nhập</a>".encode(), response.data)
        self.assertIn(b'href="/login?next=', response.data)
        with self.client.session_transaction() as current_session:
            self.assertEqual(current_session["login_next"], "/cart")

    def test_receipt_requires_a_valid_signed_order_token(self):
        response = self.client.get("/orders/31/confirmation/invalid")
        self.assertEqual(response.status_code, 404)

    def test_checkout_rejects_unavailable_installment_term_before_database_write(self):
        with patch.object(
            store_app,
            "get_connection",
            side_effect=AssertionError("Invalid form must not access the database."),
        ):
            response = self.client.post(
                "/checkout",
                data={
                    "csrf_token": "checkout-test-token",
                    "full_name": "Test Customer",
                    "phone": "0912345678",
                    "shipping_address": "Test address",
                    "payment_method": "credit_installment",
                    "installment_months": "24",
                },
            )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
