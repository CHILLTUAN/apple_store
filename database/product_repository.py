from database.connection import get_connection
from database.utils import rows_to_dicts


def get_home_products(search=""):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            WITH RankedProducts AS (
                SELECT c.category_id, c.category_name,
                    p.product_id, p.product_name, p.color, p.price,
                    p.stock_quantity, p.is_active, p.created_at,
                    img.image_url,
                    ROW_NUMBER() OVER (
                        PARTITION BY c.category_id
                        ORDER BY p.created_at DESC, p.product_id DESC
                    ) AS row_num
                FROM Categories AS c
                JOIN Products AS p ON c.category_id = p.category_id
                OUTER APPLY (
                    SELECT TOP 1 pi.image_url
                    FROM ProductImages AS pi
                    WHERE pi.product_id = p.product_id
                    ORDER BY pi.is_primary DESC, pi.image_id ASC
                ) AS img
                WHERE c.is_active = 1 AND p.is_active = 1
            )
            SELECT *
            FROM RankedProducts
            WHERE row_num <= 4
                AND (? = N'' OR product_name LIKE N'%' + ? + N'%')
            ORDER BY category_id ASC, row_num ASC;
            """,
            (search, search),
        )
        return rows_to_dicts(cursor)
    finally:
        conn.close()


def get_admin_products(search="", include_all=False):
    if not include_all:
        return get_home_products(search)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT p.product_id, p.product_name, p.color, p.price, p.stock_quantity,
                p.is_active, c.category_name, img.image_url
            FROM Products AS p
            JOIN Categories AS c ON c.category_id = p.category_id
            OUTER APPLY (
                SELECT TOP 1 pi.image_url
                FROM ProductImages AS pi
                WHERE pi.product_id = p.product_id
                ORDER BY pi.is_primary DESC, pi.image_id ASC
            ) AS img
            WHERE (? = N'' OR p.product_name LIKE N'%' + ? + N'%')
            ORDER BY p.created_at DESC, p.product_id DESC;
            """,
            (search, search),
        )
        return rows_to_dicts(cursor)
    finally:
        conn.close()
