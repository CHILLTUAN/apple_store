import unittest
from unittest.mock import patch

import app as store_app


PRODUCT_COLUMNS = (
    "product_id",
    "category_id",
    "product_name",
    "color",
    "description",
    "price",
    "stock_quantity",
    "is_active",
    "created_at",
    "ram",
    "rom",
    "charger_power",
    "category_name",
    "slug",
    "image_url",
)

VARIANT_COLUMNS = (
    "product_id",
    "color",
    "ram",
    "rom",
    "charger_power",
    "price",
    "stock_quantity",
    "is_active",
)


class ProductDetailCursor:
    def __init__(self):
        self.description = []
        self.rows = []

    def execute(self, query, params=()):
        if "SELECT p.*, c.category_name" in query:
            self.description = [(column,) for column in PRODUCT_COLUMNS]
            product_id = 4 if "AND p.category_id = ?" in query else 8
            rom = "512GB" if product_id == 4 else "1TB"
            active = True
            stock = 0 if product_id == 4 else 3
            price = 45490000 if product_id == 4 else 53290000
            self.rows = [(
                product_id,
                1,
                "MacBook Air 13 inch M5 32GB",
                "Xanh Da Trời",
                f"RAM 32GB, SSD {rom}, sạc 35W",
                price,
                stock,
                active,
                None,
                "32GB",
                rom,
                "35W",
                "Mac",
                "mac",
                None,
            )]
        else:
            self.description = [(column,) for column in VARIANT_COLUMNS]
            self.rows = [
                (2, "Bạc", "32GB", "512GB", "35W", 45490000, 4, True),
                (4, "Xanh Da Trời", "32GB", "512GB", "35W", 45490000, 0, True),
                (8, "Xanh Da Trời", "32GB", "1TB", "35W", 53290000, 3, True),
            ]

    def fetchall(self):
        return self.rows


class ProductDetailConnection:
    def __init__(self):
        self.test_cursor = ProductDetailCursor()

    def cursor(self):
        return self.test_cursor

    def close(self):
        pass


class ProductDetailTests(unittest.TestCase):
    def test_rom_choices_include_matching_storage_even_when_color_differs(self):
        connection = ProductDetailConnection()
        with (
            patch.object(store_app, "get_connection", return_value=connection),
            patch.object(store_app, "get_categories", return_value=[]),
        ):
            response = store_app.app.test_client().get("/products/8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Tùy chọn ROM".encode(), response.data)
        self.assertIn(b"512GB", response.data)
        self.assertIn(b"1TB", response.data)
        self.assertIn(b'href="/products/8?variant_id=4"', response.data)

    def test_selecting_out_of_stock_rom_disables_add_to_cart(self):
        connection = ProductDetailConnection()
        with (
            patch.object(store_app, "get_connection", return_value=connection),
            patch.object(store_app, "get_categories", return_value=[]),
        ):
            response = store_app.app.test_client().get(
                "/products/8?variant_id=4"
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Tùy chọn ROM".encode(), response.data)
        self.assertIn(b"<dd>512GB</dd>", response.data)
        self.assertIn("Hết hàng".encode(), response.data)
        self.assertIn(b'action="/cart/items/4"', response.data)
        self.assertIn(b'class="buy-product-button" type="submit" disabled', response.data)


if __name__ == "__main__":
    unittest.main()
