import unittest
from datetime import datetime
from unittest.mock import patch

from werkzeug.security import generate_password_hash

import app as store_app
from routes import sales as sales_routes


STAFF = (7, "Sales Staff", "SALESTAFF", generate_password_hash("87654321"), 2, True)


class SalesCursor:
    executions = []
    listed_order_status = "Chờ duyệt"
    referenced_product = False

    def __init__(self):
        self.row = None
        self.rows = []
        self.description = []
        self.rowcount = 1

    def execute(self, query, params=()):
        self.executions.append((query, params))
        self.row = None
        self.rows = []
        self.description = []
        if "SELECT user_id, full_name, password_hash, role, is_active" in query:
            if params[0] == STAFF[2]:
                self.row = (STAFF[0], STAFF[1], STAFF[3], STAFF[4], STAFF[5])
        elif "SELECT user_id, full_name, username, role, is_active" in query:
            if params[0] == STAFF[0]:
                self.row = (STAFF[0], STAFF[1], STAFF[2], STAFF[4], STAFF[5])
        elif "SELECT category_id, category_name, slug, image_url, is_active" in query:
            self.description = [
                (name,)
                for name in (
                    "category_id",
                    "category_name",
                    "slug",
                    "image_url",
                    "is_active",
                )
            ]
            self.rows = [(3, "iPhone", "iphone", None, True)]
        elif "SELECT category_id\n                    FROM Categories" in query:
            self.row = None
        elif "SELECT product_id FROM Products WITH" in query:
            self.row = (10,)
        elif "SELECT TOP 1 order_id" in query and "OrderDetails" in query:
            self.row = (5,) if self.referenced_product else None
        elif "AS pending_orders" in query:
            names = ("pending_orders", "orders_today", "revenue_today", "revenue_month")
            self.description = [(name,) for name in names]
            self.rows = [(2, 4, 5000, 12000)]
        elif "SELECT TOP 8" in query:
            self.description = [
                (name,)
                for name in (
                    "order_id",
                    "full_name",
                    "order_date",
                    "total_amount",
                    "order_status",
                )
            ]
            self.rows = [
                (
                    5,
                    "Test Customer",
                    datetime(2026, 11, 3, 10, 30),
                    25000,
                    "Chờ duyệt",
                )
            ]
        elif "SELECT TOP 250" in query:
            self.description = [
                (name,)
                for name in (
                    "order_id",
                    "full_name",
                    "phone",
                    "order_date",
                    "total_amount",
                    "payment_method",
                    "shipping_address",
                    "order_status",
                )
            ]
            self.rows = [
                (
                    5,
                    "Test Customer",
                    "0912345678",
                    datetime(2026, 11, 3, 10, 30),
                    25000,
                    "Cash",
                    "Test address",
                    self.listed_order_status,
                )
            ]
        elif "SELECT o.order_id, o.order_date" in query:
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
                    "email",
                )
            ]
            self.rows = [
                (
                    5,
                    datetime(2026, 11, 3, 10, 30),
                    25000,
                    "Cash",
                    "Unpaid",
                    "Test address",
                    0,
                    "Chờ duyệt",
                    None,
                    "Test Customer",
                    "0912345678",
                    None,
                )
            ]
        elif "SELECT p.product_name, p.color, d.quantity" in query:
            self.description = [
                ("product_name",),
                ("color",),
                ("quantity",),
                ("unit_price",),
                ("engraving_text",),
                ("line_total",),
            ]
            self.rows = [("iPhone", "Black", 1, 25000, None, 25000)]
        elif "COUNT(*) AS order_count" in query:
            self.description = [("order_count",), ("revenue",)]
            self.rows = [(0, 0)]
        elif "AS quantity_sold" in query:
            self.description = [
                ("product_name",),
                ("quantity_sold",),
                ("revenue",),
            ]

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class SalesConnection:
    def cursor(self):
        return SalesCursor()

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class SalesAuthenticationTests(unittest.TestCase):
    def setUp(self):
        SalesCursor.executions = []
        SalesCursor.listed_order_status = "Chờ duyệt"
        SalesCursor.referenced_product = False
        store_app.app.config.update(TESTING=True, SECRET_KEY="sales-test-secret")
        self.client = store_app.app.test_client()
        self.categories_patch = patch.object(
            store_app, "get_categories", return_value=[]
        )
        self.app_connection_patch = patch.object(
            store_app, "get_connection", side_effect=SalesConnection
        )
        self.sales_connection_patch = patch.object(
            sales_routes, "get_connection", side_effect=SalesConnection
        )
        self.categories_patch.start()
        self.app_connection_patch.start()
        self.sales_connection_patch.start()
        self.addCleanup(self.categories_patch.stop)
        self.addCleanup(self.app_connection_patch.stop)
        self.addCleanup(self.sales_connection_patch.stop)

    def _csrf_token(self):
        self.client.get("/login")
        with self.client.session_transaction() as current_session:
            return current_session["csrf_token"]

    def test_sales_staff_login_opens_sales_workspace(self):
        response = self.client.post(
            "/login",
            data={
                "username": "SALESTAFF",
                "password": "87654321",
                "csrf_token": self._csrf_token(),
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/staff/")
        with self.client.session_transaction() as current_session:
            self.assertEqual(current_session["sales_staff_id"], STAFF[0])
            self.assertNotIn("admin_user_id", current_session)

        dashboard = self.client.get("/staff/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Sales Staff", dashboard.data)
        self.assertIn(b"Doanh thu h\xc3\xb4m nay", dashboard.data)

    def test_staff_dashboard_hides_cancelled_recent_orders(self):
        with self.client.session_transaction() as current_session:
            current_session["sales_staff_id"] = STAFF[0]

        dashboard = self.client.get("/staff/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Test Customer", dashboard.data)
        recent_orders_query = next(
            query
            for query, _ in SalesCursor.executions
            if "SELECT TOP 8" in query
        )
        self.assertIn("o.order_status <> N'Đã hủy'", recent_orders_query)

    def test_sales_staff_cannot_open_admin_pages(self):
        with self.client.session_transaction() as current_session:
            current_session["sales_staff_id"] = STAFF[0]
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/login?next="))

    def test_sales_workspace_requires_login(self):
        response = self.client.get("/staff/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].startswith("/login?next="))

    def test_orders_and_date_filtered_reports_render(self):
        with self.client.session_transaction() as current_session:
            current_session["sales_staff_id"] = STAFF[0]

        orders = self.client.get(
            "/staff/orders?from_date=2026-11-01&to_date=2026-11-03"
        )
        self.assertEqual(orders.status_code, 200)
        self.assertIn(b"Test Customer", orders.data)
        self.assertIn(b"Duy\xe1\xbb\x87t \xc4\x91\xc6\xa1n", orders.data)
        self.assertIn(b"Kh\xc3\xb4ng duy\xe1\xbb\x87t", orders.data)
        self.assertIn('value="Đang chuẩn bị"'.encode("utf-8"), orders.data)
        self.assertIn('value="Đã hủy"'.encode("utf-8"), orders.data)
        self.assertIn("<th>Trạng thái</th><th>Hóa đơn</th>".encode("utf-8"), orders.data)

        report = self.client.get(
            "/staff/reports?from_date=2026-11-01&to_date=2026-11-03"
        )
        self.assertEqual(report.status_code, 200)
        self.assertIn("Báo cáo bán hàng".encode(), report.data)

    def test_preparing_order_shows_status_line_and_cancel_delivery_button(self):
        SalesCursor.listed_order_status = "Đang chuẩn bị"
        with self.client.session_transaction() as current_session:
            current_session["sales_staff_id"] = STAFF[0]

        response = self.client.get("/staff/orders")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Đang chuẩn bị".encode("utf-8"), response.data)
        self.assertIn("Hủy giao".encode("utf-8"), response.data)
        self.assertIn('value="Đã hủy"'.encode("utf-8"), response.data)
        self.assertNotIn(b">C\xe1\xba\xadp nh\xe1\xba\xadt</button>", response.data)
        self.assertNotIn(b'<select name="order_status"', response.data)

    def test_cancelling_order_hides_it_and_flashes_confirmation(self):
        with self.client.session_transaction() as current_session:
            current_session["sales_staff_id"] = STAFF[0]
            current_session["csrf_token"] = "sales-test-token"

        with patch.object(sales_routes, "update_order_status") as update_status:
            cancelled = self.client.post(
                "/staff/orders/5/status",
                data={
                    "csrf_token": "sales-test-token",
                    "order_status": "Đã hủy",
                },
            )
        self.assertEqual(cancelled.status_code, 302)
        update_status.assert_called_once()

        order_page = self.client.get(cancelled.headers["Location"])
        self.assertEqual(order_page.status_code, 200)
        self.assertIn("Đơn hàng đã được hủy".encode("utf-8"), order_page.data)
        listing_query = next(
            query
            for query, _ in SalesCursor.executions
            if "SELECT TOP 250" in query
        )
        self.assertIn("o.order_status <> N'Đã hủy'", listing_query)

    def test_invoice_and_product_pages_render(self):
        with self.client.session_transaction() as current_session:
            current_session["sales_staff_id"] = STAFF[0]

        invoice = self.client.get("/staff/orders/5/invoice")
        self.assertEqual(invoice.status_code, 200)
        self.assertIn(b"In / L\xc6\xb0u h\xc3\xb3a \xc4\x91\xc6\xa1n", invoice.data)

        with patch.object(sales_routes, "get_admin_products", return_value=[]):
            products = self.client.get("/staff/products")
        self.assertEqual(products.status_code, 200)

        with patch.object(sales_routes, "_product_categories", return_value=[]):
            product_form = self.client.get("/staff/products/new")
        self.assertEqual(product_form.status_code, 200)

    def test_staff_can_manage_categories_and_product_actions(self):
        with self.client.session_transaction() as current_session:
            current_session["sales_staff_id"] = STAFF[0]
            current_session["csrf_token"] = "sales-test-token"

        with patch.object(
            sales_routes,
            "_categories",
            return_value=[
                {
                    "category_id": 3,
                    "category_name": "iPhone",
                    "slug": "iphone",
                    "is_active": True,
                }
            ],
        ):
            categories = self.client.get("/staff/categories")
        self.assertEqual(categories.status_code, 200)
        self.assertIn(b"iPhone", categories.data)
        self.assertIn(b"/staff/categories/3/edit", categories.data)

        new_category = self.client.post(
            "/staff/categories/new",
            data={
                "csrf_token": "sales-test-token",
                "category_name": "Mac",
                "slug": "mac",
                "is_active": "1",
            },
        )
        self.assertEqual(new_category.status_code, 302)
        self.assertEqual(new_category.headers["Location"], "/staff/categories")
        self.assertTrue(
            any("INSERT INTO Categories" in query for query, _ in SalesCursor.executions)
        )

        edit_category = self.client.post(
            "/staff/categories/3/edit",
            data={
                "csrf_token": "sales-test-token",
                "category_name": "iPhone updated",
                "slug": "iphone-updated",
                "is_active": "0",
            },
        )
        self.assertEqual(edit_category.status_code, 302)
        self.assertTrue(
            any("UPDATE Categories" in query for query, _ in SalesCursor.executions)
        )

        product = {
            "product_id": 10,
            "product_name": "Test iPhone",
            "color": "Black",
            "category_name": "iPhone",
            "price": 1499,
            "stock_quantity": 3,
            "is_active": False,
            "image_url": None,
        }
        with patch.object(sales_routes, "get_admin_products", return_value=[product]):
            product_page = self.client.get("/staff/products")
        self.assertEqual(product_page.status_code, 200)
        self.assertIn(b"Test iPhone", product_page.data)
        self.assertIn(b"/staff/products/10/visibility", product_page.data)
        self.assertIn(b"/staff/products/10/delete", product_page.data)

        hidden = self.client.post(
            "/staff/products/10/visibility",
            data={"csrf_token": "sales-test-token", "is_active": "0"},
        )
        self.assertEqual(hidden.status_code, 302)
        self.assertTrue(
            any("UPDATE Products SET is_active" in query for query, _ in SalesCursor.executions)
        )

        deleted = self.client.post(
            "/staff/products/10/delete",
            data={"csrf_token": "sales-test-token"},
        )
        self.assertEqual(deleted.status_code, 302)
        self.assertTrue(
            any("DELETE FROM Products" in query for query, _ in SalesCursor.executions)
        )

        SalesCursor.referenced_product = True
        blocked_delete = self.client.post(
            "/staff/products/10/delete",
            data={"csrf_token": "sales-test-token"},
        )
        self.assertEqual(blocked_delete.status_code, 302)
        blocked_delete_page = self.client.get(blocked_delete.headers["Location"])
        self.assertIn("Không thể xóa sản phẩm".encode(), blocked_delete_page.data)

    def test_reports_reject_reversed_date_ranges(self):
        with self.client.session_transaction() as current_session:
            current_session["sales_staff_id"] = STAFF[0]
        response = self.client.get(
            "/staff/reports?from_date=2026-11-04&to_date=2026-11-03"
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
