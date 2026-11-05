from database.connection import get_connection
from database.utils import rows_to_dicts


MAX_HOME_PRODUCTS_PER_CATEGORY = 50


def get_home_product_limit():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT setting_value
            FROM StoreSettings
            WHERE setting_key = N'homepage_products_per_category';
            """
        )
        setting = cursor.fetchone()
    finally:
        conn.close()

    if not setting:
        raise RuntimeError(
            "Thiếu cài đặt homepage_products_per_category. "
            "Hãy chạy database/sql/homepage_products_setting_migration.sql."
        )
    try:
        limit = int(setting[0])
    except (TypeError, ValueError) as error:
        raise RuntimeError("Cài đặt số sản phẩm trang chủ không hợp lệ.") from error
    if not 1 <= limit <= MAX_HOME_PRODUCTS_PER_CATEGORY:
        raise RuntimeError("Cài đặt số sản phẩm trang chủ nằm ngoài giới hạn cho phép.")
    return limit


def get_catalog_products(search="", category_id=None, min_price=None, max_price=None, sort="newest"):
    order_by = {
        "newest": "p.created_at DESC, p.product_id DESC",
        "price_asc": "p.price ASC, p.product_name ASC",
        "price_desc": "p.price DESC, p.product_name ASC",
        "name": "p.product_name ASC, p.product_id ASC",
    }.get(sort, "p.created_at DESC, p.product_id DESC")
    conditions = ["c.is_active = 1", "p.is_active = 1"]
    params = []
    if search:
        conditions.append(
            "(p.product_name LIKE N'%' + ? + N'%' "
            "OR c.category_name LIKE N'%' + ? + N'%')"
        )
        params.extend((search, search))
    if category_id is not None:
        conditions.append("p.category_id = ?")
        params.append(category_id)
    if min_price is not None:
        conditions.append("p.price >= ?")
        params.append(min_price)
    if max_price is not None:
        conditions.append("p.price <= ?")
        params.append(max_price)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""--sql
            SELECT p.product_id, p.product_name, p.color, p.price,
                p.stock_quantity, p.ram, p.rom, p.charger_power,
                c.category_name, c.slug, img.image_url
            FROM Products AS p
            JOIN Categories AS c ON c.category_id = p.category_id
            OUTER APPLY (
                SELECT TOP 1 pi.image_url
                FROM ProductImages AS pi
                WHERE pi.product_id = p.product_id
                ORDER BY pi.is_primary DESC, pi.image_id ASC
            ) AS img
            WHERE {" AND ".join(conditions)}
            ORDER BY {order_by};
            """,
            tuple(params),
        )
        return rows_to_dicts(cursor)
    finally:
        conn.close()


def get_home_products(search="", limit=None):
    if limit is None:
        limit = get_home_product_limit()

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
            WHERE row_num <= ?
                AND (? = N'' OR product_name LIKE N'%' + ? + N'%')
            ORDER BY category_id ASC, row_num ASC;
            """,
            (limit, search, search),
        )
        return rows_to_dicts(cursor)
    finally:
        conn.close()


def get_admin_products(search="", include_all=False):
    if not include_all:
        return [
            product
            for product in get_home_products(search)
            if product["is_active"]
        ]

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
