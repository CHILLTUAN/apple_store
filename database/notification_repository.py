from datetime import datetime

from database.connection import get_connection
from database.utils import rows_to_dicts


def create_order_notification(
    cursor, user_id, order_id, notification_type, title, message
):
    cursor.execute(
        """--sql
        INSERT INTO CustomerNotifications (
            user_id, order_id, notification_type, title, message
        )
        VALUES (?, ?, ?, ?, ?);
        """,
        (user_id, order_id, notification_type, title, message),
    )


def _readable_notifications(notifications):
    for notification in notifications:
        value = notification.get("created_at")
        if not isinstance(value, str):
            continue
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                notification["created_at"] = datetime.strptime(value, fmt)
                break
            except ValueError:
                pass
    return notifications


def get_unread_notification_count(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT COUNT(*)
            FROM CustomerNotifications
            WHERE user_id = ? AND is_read = 0;
            """,
            (user_id,),
        )
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_customer_notifications(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT notification_id, order_id, notification_type, title,
                message, is_read, created_at
            FROM CustomerNotifications
            WHERE user_id = ?
            ORDER BY created_at DESC, notification_id DESC;
            """,
            (user_id,),
        )
        return _readable_notifications(rows_to_dicts(cursor))
    finally:
        conn.close()


def mark_customer_notifications_read(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            UPDATE CustomerNotifications
            SET is_read = 1
            WHERE user_id = ? AND is_read = 0;
            """,
            (user_id,),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_customer_notification(user_id, notification_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            DELETE FROM CustomerNotifications
            WHERE notification_id = ? AND user_id = ?;
            """,
            (notification_id, user_id),
        )
        deleted = cursor.rowcount == 1
        conn.commit()
        return deleted
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
