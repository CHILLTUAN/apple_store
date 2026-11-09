from database.notification_repository import create_order_notification


class OrderNotFoundError(LookupError):
    pass


class OrderStatusTransitionError(ValueError):
    pass


ORDER_TRANSITIONS = {
    "Chờ duyệt": ("Đang chuẩn bị", "Đã hủy"),
    "Đang chuẩn bị": ("Đang giao", "Đã giao", "Đã hủy"),
    "Đang giao": ("Đã giao", "Đã hủy"),
    "Đã giao": (),
    "Đã hủy": (),
}

ORDER_STATUS_OPTIONS = {
    status: (status, *next_statuses)
    for status, next_statuses in ORDER_TRANSITIONS.items()
}


def _notify_order_completed(cursor, user_id, order_id):
    create_order_notification(
        cursor,
        user_id,
        order_id,
        "order_completed",
        "Đơn hàng đã hoàn tất",
        f"Đơn hàng #{order_id} đã được giao hoàn tất. Cảm ơn bạn đã mua hàng.",
    )


def update_order_status(cursor, order_id, new_status):
    cursor.execute(
        "SELECT product_id FROM OrderDetails WHERE order_id = ? ORDER BY product_id;",
        (order_id,),
    )
    product_ids = [row[0] for row in cursor.fetchall()]
    for product_id in product_ids:
        cursor.execute(
            """--sql
            SELECT product_id FROM Products WITH (UPDLOCK, ROWLOCK)
            WHERE product_id = ?;
            """,
            (product_id,),
        )
        if not cursor.fetchone():
            raise OrderStatusTransitionError(
                "Không tìm thấy sản phẩm trong đơn hàng."
            )

    cursor.execute(
        """--sql
        SELECT order_status, stock_committed, user_id
        FROM Orders WITH (UPDLOCK, ROWLOCK)
        WHERE order_id = ?;
        """,
        (order_id,),
    )
    order = cursor.fetchone()
    if not order:
        raise OrderNotFoundError

    current_status, stock_committed, user_id = order
    if current_status == new_status:
        return
    if new_status not in ORDER_TRANSITIONS.get(current_status, ()):
        raise OrderStatusTransitionError(
            "Trạng thái đơn hàng không thể chuyển theo bước này."
        )

    if new_status == "Đã hủy":
        if stock_committed:
            cursor.execute(
                "SELECT product_id, quantity FROM OrderDetails WHERE order_id = ?;",
                (order_id,),
            )
            for product_id, quantity in cursor.fetchall():
                cursor.execute(
                    """--sql
                    UPDATE Products
                    SET stock_quantity = stock_quantity + ?
                    WHERE product_id = ?;
                    """,
                    (quantity, product_id),
                )
        cursor.execute(
            """--sql
            UPDATE Orders
            SET order_status = N'Đã hủy', stock_committed = 0
            WHERE order_id = ?;
            """,
            (order_id,),
        )
        title = (
            "Đơn hàng chưa được duyệt"
            if current_status == "Chờ duyệt"
            else "Đơn hàng đã bị hủy"
        )
        message = (
            f"Đơn hàng #{order_id} không được duyệt và đã bị hủy."
            if current_status == "Chờ duyệt"
            else f"Đơn hàng #{order_id} đã bị hủy."
        )
        create_order_notification(
            cursor,
            user_id,
            order_id,
            "order_rejected",
            title,
            message,
        )
        return

    if not stock_committed:
        cursor.execute(
            "SELECT product_id, quantity FROM OrderDetails WHERE order_id = ?;",
            (order_id,),
        )
        for product_id, quantity in cursor.fetchall():
            cursor.execute(
                """--sql
                UPDATE Products
                SET stock_quantity = stock_quantity - ?
                WHERE product_id = ? AND stock_quantity >= ?;
                """,
                (quantity, product_id, quantity),
            )
            if cursor.rowcount != 1:
                raise OrderStatusTransitionError(
                    "Tồn kho không đủ để duyệt đơn hàng."
                )
        cursor.execute(
            """--sql
            UPDATE Orders
            SET order_status = ?, stock_committed = 1
            WHERE order_id = ?;
            """,
            (new_status, order_id),
        )
        if new_status == "Đã giao":
            _notify_order_completed(cursor, user_id, order_id)
        elif new_status == "Đang chuẩn bị":
            create_order_notification(
                cursor,
                user_id,
                order_id,
                "order_approved",
                "Đơn hàng đã được duyệt",
                f"Đơn hàng #{order_id} đã được duyệt và đang được chuẩn bị.",
            )
        return

    cursor.execute(
        "UPDATE Orders SET order_status = ? WHERE order_id = ?;",
        (new_status, order_id),
    )
    if new_status == "Đã giao":
        _notify_order_completed(cursor, user_id, order_id)
    if new_status == "Đang chuẩn bị":
        create_order_notification(
            cursor,
            user_id,
            order_id,
            "order_approved",
            "Đơn hàng đã được duyệt",
            f"Đơn hàng #{order_id} đã được duyệt và đang được chuẩn bị.",
        )
