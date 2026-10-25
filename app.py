from flask import Flask, render_template
from database.category_repository import get_categories
from database.connection import get_connection
from database.utils import rows_to_dicts

app = Flask(__name__)

def format_vnd(price):
    return f"{price:,.0f}".replace(',', '.') + " ₫"
# Đăng ký hàm thành filter để Jinja có thể sử dụng trong template.
app.jinja_env.filters["vnd"] = format_vnd

@app.context_processor 
# Đăng ký hàm cung cấp biến dùng chung cho template
def provide_categories():
    return {
        "categories": get_categories()
    }

@app.route("/")
def home():
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute(
            """--sql
            WITH RankedProducts AS (
                SELECT c.category_id, 
                c.category_name,
                p.product_id, 
                p.product_name,  
                p.color, 
                p.price, 
                p.created_at,
                img.image_url,
                ROW_NUMBER () OVER (
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
            ) SELECT * 
            FROM RankedProducts
            WHERE row_num <= 4
            ORDER BY category_id ASC, row_num ASC
            """
        )
        products = rows_to_dicts(cursor)

        products_by_category = {}
        for product in products:
            products_by_category.setdefault(product["category_name"], []).append(product)
    finally:
        conn.close()

    return render_template(
        "home/index.html",
        store_name="Apple Store",
        products_by_category=products_by_category
    )

# /mac /ipad /iphone /watch /airpods /phu-kien
@app.route("/<category_slug>")
def category_page(category_slug):

    categories_map = {}
    for record in get_categories():        
        categories_map[record["slug"]] = record
    
    category = categories_map.get(category_slug, None)
    if category is None:
        return "Không tìm thấy danh mục", 404
    # Phòng trường hợp /login, /register, . . .

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""--sql
            SELECT p.*, img.image_url  
            FROM Products as p
            OUTER APPLY (
                SELECT TOP 1 pi.image_url
                FROM ProductImages AS pi
                WHERE pi.product_id = p.product_id
                ORDER BY pi.is_primary DESC, pi.image_id ASC
            ) AS img
            WHERE p.category_id = ?
                AND p.is_active = 1
            ORDER BY p.created_at DESC, p.product_id ASC;
        """,
        (category["category_id"],)
        )
        # Dấu ? thứ mấy tương ứng với giá trị thứ mấy trong tuple.
        products = rows_to_dicts(cursor)

        products_by_name = {}
        for product in products:
            name = product["product_name"]

            x = products_by_name.setdefault(
                name,
                {
                    "product_name": name,
                    "image_url": product["image_url"], 
                    "descriptions": []
                } 
            )
            temp = {"ram": product["ram"], "rom": product["rom"], "charger_power": product["charger_power"], "price": product["price"]}
            if temp not in x["descriptions"]:
                x["descriptions"].append(temp)
    finally:
        conn.close()
    return render_template(
        "products/list.html",
        store_name="Apple Store",
        category_name=category["category_name"],
        products=list(products_by_name.values())
    )

@app.route("/login")
def login():
    return render_template(
        "auth/login.html",
        store_name="Apple Store",
        message="Flask đã kết nối với HTML thành công!"
    )

@app.route("/register")
def register():
    return render_template(
        "auth/register.html",
        store_name="Apple Store",
        message="Flask đã kết nối với HTML thành công!"
    )


if __name__ == "__main__":
    app.run(debug=True)