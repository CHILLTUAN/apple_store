import unittest
from datetime import datetime
from unittest.mock import patch

import app as store_app


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
        elif "INSERT INTO Users" in query:
            self.row = (21,)
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
        self.categories_patch.start()
        self.connection_patch.start()
        self.addCleanup(self.categories_patch.stop)
        self.addCleanup(self.connection_patch.stop)
        with self.client.session_transaction() as current_session:
            current_session["csrf_token"] = "checkout-test-token"
            current_session["cart"] = {"10": 1}
            current_session["cart_engraving"] = {"10": "For Linh"}

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

        detail_insert = next(
            params
            for query, params in self.connection.test_cursor.executions
            if "INSERT INTO OrderDetails" in query
        )
        self.assertEqual(detail_insert[-1], "For Linh")
        customer_insert = next(
            params
            for query, params in self.connection.test_cursor.executions
            if "INSERT INTO Users" in query
        )
        self.assertEqual(customer_insert[0:2], ("Test Customer", "0912345678"))
        self.assertRegex(
            customer_insert[2], r"^guest_[0-9a-f]{32}@guest\.apple-store\.local$"
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
