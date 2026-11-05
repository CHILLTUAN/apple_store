import unittest
from unittest.mock import patch

from database import product_repository


class ProductCursor:
    def __init__(self):
        self.query = ""
        self.params = ()
        self.description = []

    def execute(self, query, params=()):
        self.query = query
        self.params = params

    def fetchall(self):
        return []


class ProductConnection:
    def __init__(self):
        self.test_cursor = ProductCursor()

    def cursor(self):
        return self.test_cursor

    def close(self):
        pass


class HomeProductQueryTests(unittest.TestCase):
    def test_homepage_query_filters_hidden_products_before_applying_limit(self):
        connection = ProductConnection()
        with (
            patch.object(product_repository, "get_home_product_limit", return_value=4),
            patch.object(
                product_repository, "get_connection", return_value=connection
            ),
        ):
            products = product_repository.get_home_products()

        self.assertEqual(products, [])
        self.assertIn(
            "WHERE c.is_active = 1 AND p.is_active = 1",
            connection.test_cursor.query,
        )
        self.assertIn("WHERE row_num <= ?", connection.test_cursor.query)
        self.assertEqual(connection.test_cursor.params, (4, "", ""))

    def test_homepage_only_admin_list_discards_hidden_products(self):
        products = [
            {"product_id": 1, "is_active": True},
            {"product_id": 2, "is_active": False},
        ]
        with patch.object(
            product_repository, "get_home_products", return_value=products
        ):
            visible_products = product_repository.get_admin_products()

        self.assertEqual(visible_products, [products[0]])


if __name__ == "__main__":
    unittest.main()
