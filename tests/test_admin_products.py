import unittest
from unittest.mock import patch

import app as store_app
from routes import admin as admin_routes


class AdminIdentityCursor:
    def execute(self, *_):
        self.row = (1, "Store Admin", "admin", 1, True)

    def fetchone(self):
        return self.row


class AdminIdentityConnection:
    def cursor(self):
        return AdminIdentityCursor()

    def close(self):
        pass


class AdminProductReadOnlyTests(unittest.TestCase):
    def setUp(self):
        store_app.app.config.update(TESTING=True, SECRET_KEY="product-admin-test-secret")
        self.client = store_app.app.test_client()

        with self.client.session_transaction() as current_session:
            current_session["admin_user_id"] = 1
            current_session["csrf_token"] = "product-admin-test-token"
        self.connection_patch = patch.object(
            admin_routes, "get_connection", return_value=AdminIdentityConnection()
        )
        self.connection_patch.start()
        self.addCleanup(self.connection_patch.stop)

    def test_admin_product_list_is_read_only(self):
        hidden_product = {
            "product_id": 10,
            "product_name": "Test iPhone",
            "color": "Black",
            "category_name": "iPhone",
            "price": 1499,
            "stock_quantity": 3,
            "is_active": False,
            "image_url": None,
        }
        with patch.object(
            admin_routes, "get_admin_products", return_value=[hidden_product]
        ):
            response = self.client.get("/admin/products")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test iPhone", response.data)
        self.assertIn(b"3 s\xe1\xba\xa3n ph\xe1\xba\xa9m trong kho", response.data)
        self.assertNotIn(b"Black", response.data)
        self.assertNotIn(b"iPhone</td>", response.data)
        self.assertNotIn(b"1.499", response.data)
        self.assertNotIn("Đã ẩn".encode(), response.data)
        self.assertNotIn("Đang bán".encode(), response.data)
        self.assertNotIn(">Xóa<".encode(), response.data)
        self.assertNotIn(">Sửa<".encode(), response.data)
        self.assertNotIn("Thêm sản phẩm".encode(), response.data)

    def test_admin_product_list_shows_all_rows_and_stock_amounts(self):
        visible_product = {
            "product_id": 11,
            "product_name": "Visible iPhone",
            "color": "White",
            "category_name": "iPhone",
            "price": 1499,
            "stock_quantity": 3,
            "is_active": True,
            "image_url": None,
        }
        hidden_product = {
            **visible_product,
            "product_id": 10,
            "product_name": "Hidden iPhone",
            "is_active": False,
        }

        with patch.object(
            admin_routes,
            "get_admin_products",
            return_value=[visible_product, hidden_product],
        ) as get_products:
            products_list = self.client.get("/admin/products")

        self.assertEqual(products_list.status_code, 200)
        self.assertIn(b"Visible iPhone", products_list.data)
        self.assertIn(b"Hidden iPhone", products_list.data)
        self.assertIn("Tất cả sản phẩm".encode(), products_list.data)
        self.assertIn(b"6 s\xe1\xba\xa3n ph\xe1\xba\xa9m trong kho", products_list.data)
        self.assertNotIn("Chỉ xem sản phẩm trên trang chủ".encode(), products_list.data)
        get_products.assert_called_once_with("", include_all=True)

    def test_admin_cannot_access_product_mutations_categories_or_billing(self):
        restricted_get_urls = (
            "/admin/products/new",
            "/admin/products/10/edit",
            "/admin/categories",
            "/admin/categories/new",
            "/admin/orders",
            "/admin/orders/1/invoice",
        )

        for path in restricted_get_urls:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)

        for path in (
            "/admin/products/10/delete",
            "/admin/products/10/visibility",
            "/admin/orders/1/status",
        ):
            with self.subTest(path=path):
                response = self.client.post(
                    path,
                    data={"csrf_token": "product-admin-test-token"},
                )
                self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
