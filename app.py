import hmac
import os
import secrets
from urllib.parse import urlsplit

import click
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from database.category_repository import get_categories
from database.connection import get_connection
from database.product_repository import get_home_products
from database.utils import rows_to_dicts
from routes.admin import admin_bp

load_dotenv()

app = Flask(__name__)
app.register_blueprint(admin_bp)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
if not app.config["SECRET_KEY"]:
    app.config["SECRET_KEY"] = secrets.token_hex(32)
    app.logger.warning(
        "FLASK_SECRET_KEY is not set; sessions will be invalidated when the app restarts."
    )

def format_vnd(price):
    return f"{price:,.0f}".replace(',', '.') + " ₫"
# Đăng ký hàm thành filter để Jinja có thể sử dụng trong template.
app.jinja_env.filters["vnd"] = format_vnd

@app.context_processor 
# Đăng ký hàm cung cấp biến dùng chung cho template
def provide_categories():
    if request.blueprint == "admin":
        return {"categories": []}
    return {
        "categories": get_categories()
    }

@app.before_request
def protect_authentication_forms():
    if request.endpoint in ("login", "logout"):
        session.setdefault("csrf_token", secrets.token_urlsafe(32))
        if request.method == "POST" and not hmac.compare_digest(
            session["csrf_token"], request.form.get("csrf_token", "")
        ):
            abort(400, description="Yêu cầu không hợp lệ hoặc đã hết hạn.")


@app.route("/")
def home():
    products = get_home_products()
    products_by_category = {}
    for product in products:
        products_by_category.setdefault(product["category_name"], []).append(product)

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
                    "product_id": product["product_id"],
                    "descriptions": []
                } 
            )
            option = {
                "product_id": product["product_id"],
                "ram": product["ram"],
                "rom": product["rom"],
                "charger_power": product["charger_power"],
                "price": product["price"],
            }
            if not any(
                all(
                    existing[field] == option[field]
                    for field in ("ram", "rom", "charger_power", "price")
                )
                for existing in x["descriptions"]
            ):
                x["descriptions"].append(option)
    finally:
        conn.close()
    return render_template(
        "products/list.html",
        store_name="Apple Store",
        category_name=category["category_name"],
        products=list(products_by_name.values())
    )

@app.route("/products/<int:product_id>")
def product_detail(product_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT p.*, c.category_name, c.slug, img.image_url
            FROM Products AS p
            JOIN Categories AS c ON c.category_id = p.category_id
            OUTER APPLY (
                SELECT TOP 1 pi.image_url
                FROM ProductImages AS pi
                WHERE pi.product_id = p.product_id
                ORDER BY pi.is_primary DESC, pi.image_id ASC
            ) AS img
            WHERE p.product_id = ? AND p.is_active = 1;
            """,
            (product_id,),
        )
        products = rows_to_dicts(cursor)
        color_options = []
        rom_options = []
        if products:
            product = products[0]
            cursor.execute(
                """--sql
                SELECT product_id, color, ram, rom, charger_power, price
                FROM Products
                WHERE category_id = ?
                    AND product_name = ?
                    AND is_active = 1
                    AND color IS NOT NULL
                ORDER BY product_id ASC;
                """,
                (product["category_id"], product["product_name"]),
            )
            variants = rows_to_dicts(cursor)
            same_configuration = (
                product["ram"],
                product["rom"],
                product["charger_power"],
            )
            for variant in variants:
                if any(option["color"] == variant["color"] for option in color_options):
                    continue
                matching_variant = next(
                    (
                        candidate
                        for candidate in variants
                        if candidate["color"] == variant["color"]
                        and (
                            candidate["ram"],
                            candidate["rom"],
                            candidate["charger_power"],
                        )
                        == same_configuration
                    ),
                    variant,
                )
                color_options.append(matching_variant)
            for variant in variants:
                if any(option["rom"] == variant["rom"] for option in rom_options):
                    continue
                matching_variant = next(
                    (
                        candidate
                        for candidate in variants
                        if candidate["rom"] == variant["rom"]
                        and candidate["color"] == product["color"]
                        and (
                            candidate["ram"],
                            candidate["charger_power"],
                        )
                        == (
                            product["ram"],
                            product["charger_power"],
                        )
                    ),
                    variant,
                )
                rom_options.append(matching_variant)
    finally:
        conn.close()

    if not products:
        abort(404)

    return render_template(
        "products/detail.html",
        store_name="Apple Store",
        product=products[0],
        color_options=color_options,
        rom_options=rom_options,
    )

@app.route("/cart")
def cart_page():
    cart = session.get("cart", {})
    if not cart:
        return render_template("cart/index.html", store_name="Apple Store", items=[], total=0)

    product_ids = [int(product_id) for product_id in cart]
    placeholders = ", ".join("?" for _ in product_ids)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""--sql
            SELECT p.product_id, p.product_name, p.color, p.price, img.image_url
            FROM Products AS p
            OUTER APPLY (
                SELECT TOP 1 pi.image_url
                FROM ProductImages AS pi
                WHERE pi.product_id = p.product_id
                ORDER BY pi.is_primary DESC, pi.image_id ASC
            ) AS img
            WHERE p.product_id IN ({placeholders}) AND p.is_active = 1;
            """,
            tuple(product_ids),
        )
        products = rows_to_dicts(cursor)
    finally:
        conn.close()

    items = []
    for product in products:
        product["quantity"] = cart.get(str(product["product_id"]), 0)
        product["line_total"] = product["price"] * product["quantity"]
        items.append(product)

    total = sum((item["line_total"] for item in items), 0)
    return render_template(
        "cart/index.html",
        store_name="Apple Store",
        items=items,
        total=total,
    )

@app.post("/cart/items/<int:product_id>")
def add_to_cart(product_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT product_id FROM Products WHERE product_id = ? AND is_active = 1;",
            (product_id,),
        )
        if not cursor.fetchone():
            abort(404)
    finally:
        conn.close()

    cart = session.get("cart", {})
    product_key = str(product_id)
    cart[product_key] = cart.get(product_key, 0) + 1
    session["cart"] = cart
    flash("Sản phẩm đã được thêm vào giỏ hàng", "success")
    return redirect(url_for("home"))

@app.post("/cart/items/<int:product_id>/remove")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    cart.pop(str(product_id), None)
    session["cart"] = cart
    return redirect(url_for("cart_page"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """--sql
                SELECT user_id, full_name, password_hash, role, is_active
                FROM Users
                WHERE username = ?;
                """,
                (username,),
            )
            user = cursor.fetchone()
        finally:
            conn.close()

        if (
            user
            and user[3] == 1
            and user[4]
            and check_password_hash(user[2], password)
        ):
            session.pop("csrf_token", None)
            session["admin_user_id"] = user[0]
            session.permanent = request.form.get("remember_me") == "on"
            next_url = request.args.get("next", "")
            parsed_next_url = urlsplit(next_url)
            if (
                next_url.startswith("/")
                and not next_url.startswith("//")
                and "\\" not in next_url
                and not parsed_next_url.netloc
                and not parsed_next_url.scheme
            ):
                return redirect(next_url)
            return redirect(url_for("admin.dashboard"))

        flash("Thông tin đăng nhập không hợp lệ hoặc tài khoản không có quyền quản trị.", "error")

    return render_template(
        "auth/login.html",
        store_name="Apple Store",
        csrf_token=session.get("csrf_token", ""),
    )

@app.post("/logout")
def logout():
    session.pop("admin_user_id", None)
    session.pop("csrf_token", None)
    flash("Bạn đã đăng xuất.", "success")
    return redirect(url_for("login"))


@app.cli.command("create-admin")
def create_admin():
    """Create the first administrator account without exposing credentials in source."""
    username = click.prompt("Tên đăng nhập")
    full_name = click.prompt("Họ và tên")
    password = click.prompt(
        "Mật khẩu", hide_input=True, confirmation_prompt=True
    )
    if not username.strip() or not full_name.strip() or not password:
        raise click.ClickException("Tên đăng nhập, họ tên và mật khẩu không được để trống.")
    if len(password) < 8:
        raise click.ClickException("Mật khẩu phải có ít nhất 8 ký tự.")

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM Users WHERE username = ?;", (username.strip(),))
        if cursor.fetchone():
            raise click.ClickException("Tên đăng nhập đã tồn tại.")

        cursor.execute(
            """--sql
            INSERT INTO Users (full_name, username, password_hash, role, is_active)
            VALUES (?, ?, ?, 1, 1);
            """,
            (
                full_name.strip(),
                username.strip(),
                generate_password_hash(password),
            ),
        )
        conn.commit()
    finally:
        conn.close()

    click.echo("Tài khoản quản trị đã được tạo.")


@app.route("/register")
def register():
    return render_template(
        "auth/register.html",
        store_name="Apple Store",
        message="Flask đã kết nối với HTML thành công!"
    )


if __name__ == "__main__":
    app.run(debug=True)