import unittest

from database.order_repository import (
    OrderStatusTransitionError,
    update_order_status,
)


class InventoryCursor:
    def __init__(self, status="Chờ duyệt", stock_committed=False, stock=5):
        self.status = status
        self.stock_committed = stock_committed
        self.stock = stock
        self.row = None
        self.rows = []
        self.rowcount = 0

    def execute(self, query, params=()):
        self.row = None
        self.rows = []
        self.rowcount = 0
        if "SELECT product_id FROM OrderDetails" in query:
            self.rows = [(10,)]
        elif "SELECT product_id FROM Products WITH" in query:
            self.row = (10,)
        elif "SELECT order_status, stock_committed" in query:
            self.row = (self.status, self.stock_committed)
        elif "SELECT product_id, quantity FROM OrderDetails" in query:
            self.rows = [(10, 2)]
        elif "SET stock_quantity = stock_quantity - ?" in query:
            quantity = params[0]
            if self.stock >= quantity:
                self.stock -= quantity
                self.rowcount = 1
        elif "SET stock_quantity = stock_quantity + ?" in query:
            self.stock += params[0]
            self.rowcount = 1
        elif "SET order_status = N'Đã hủy'" in query:
            self.status = "Đã hủy"
            self.stock_committed = False
        elif "SET order_status = ?, stock_committed = 1" in query:
            self.status = params[0]
            self.stock_committed = True
        elif "UPDATE Orders SET order_status = ?" in query:
            self.status = params[0]

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class OrderInventoryTests(unittest.TestCase):
    def test_approval_deducts_stock_and_cancellation_restores_it(self):
        cursor = InventoryCursor()
        update_order_status(cursor, 1, "Đang chuẩn bị")
        self.assertEqual(cursor.stock, 3)
        self.assertTrue(cursor.stock_committed)

        update_order_status(cursor, 1, "Đã hủy")
        self.assertEqual(cursor.stock, 5)
        self.assertFalse(cursor.stock_committed)

    def test_cancelling_pending_order_releases_reservation_without_stock_change(self):
        cursor = InventoryCursor()
        update_order_status(cursor, 1, "Đã hủy")
        self.assertEqual(cursor.stock, 5)
        self.assertFalse(cursor.stock_committed)

    def test_approval_fails_without_enough_stock(self):
        cursor = InventoryCursor(stock=1)
        with self.assertRaises(OrderStatusTransitionError):
            update_order_status(cursor, 1, "Đang chuẩn bị")
        self.assertEqual(cursor.status, "Chờ duyệt")


if __name__ == "__main__":
    unittest.main()
