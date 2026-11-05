import hmac
import os
import re
import secrets
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

import click
from itsdangerous import BadSignature, URLSafeSerializer
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from dotenv import load_dotenv
from werkzeug.security import check_password_hash, generate_password_hash
from database.category_repository import get_categories
from database.connection import get_connection
from database.product_repository import get_catalog_products, get_home_products
from database.utils import rows_to_dicts
from routes.admin import admin_bp
from routes.sales import sales_bp

load_dotenv()

app = Flask(__name__)
app.register_blueprint(admin_bp)
app.register_blueprint(sales_bp)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")
if not app.config["SECRET_KEY"]:
    app.config["SECRET_KEY"] = secrets.token_hex(32)
    app.logger.warning(
        "FLASK_SECRET_KEY is not set; sessions will be invalidated when the app restarts."
    )

order_receipt_serializer = URLSafeSerializer(
    app.config["SECRET_KEY"], salt="customer-order-receipt"
)


def format_vnd(price):
    return f"{price:,.0f}".replace(',', '.') + " ₫"
# Đăng ký hàm thành filter để Jinja có thể sử dụng trong template.
app.jinja_env.filters["vnd"] = format_vnd


def _require_customer_login(next_url, return_url):
    if session.get("customer_user_id") is not None:
        return None

    session["login_next"] = next_url
    flash("Để đặt hàng, vui lòng đăng nhập tài khoản của bạn.", "login_required")
    return redirect(return_url)


@app.context_processor 
# Đăng ký hàm cung cấp biến dùng chung cho template
def provide_categories():
    if request.blueprint == "admin":
        return {"categories": []}
    return {
        "categories": get_categories(),
        "csrf_token": session.setdefault("csrf_token", secrets.token_urlsafe(32)),
    }

@app.before_request
def protect_authentication_forms():
    protected_form_endpoints = {
        "login",
        "register",
        "logout",
        "logout_on_close",
        "edit_customer_account",
        "add_to_cart",
        "remove_from_cart",
        "update_cart_quantity",
        "checkout",
    }
    if request.endpoint in protected_form_endpoints:
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


def _catalog_filters(category_id=None):
    search = request.args.get("q", "").strip()
    sort = request.args.get("sort", "newest")
    if sort not in {"newest", "price_asc", "price_desc", "name"}:
        abort(400, description="Cách sắp xếp không hợp lệ.")

    prices = {}
    for field in ("min_price", "max_price"):
        raw_value = request.args.get(field, "").strip()
        if not raw_value:
            prices[field] = None
            continue
        try:
            value = Decimal(raw_value)
        except InvalidOperation:
            abort(400, description="Khoảng giá không hợp lệ.")
        if not value.is_finite() or value < 0:
            abort(400, description="Khoảng giá không hợp lệ.")
        prices[field] = value
    if (
        prices["min_price"] is not None
        and prices["max_price"] is not None
        and prices["min_price"] > prices["max_price"]
    ):
        abort(400, description="Giá thấp nhất không được lớn hơn giá cao nhất.")

    return {
        "search": search,
        "sort": sort,
        "min_price": prices["min_price"],
        "max_price": prices["max_price"],
        "category_id": category_id,
    }


@app.route("/search")
def search_products():
    filters = _catalog_filters()
    products = get_catalog_products(**filters)
    return render_template(
        "products/search.html",
        store_name="Apple Store",
        products=products,
        filters=filters,
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

    filters = _catalog_filters(category["category_id"])
    products = get_catalog_products(**filters)

    products_by_name = {}
    for product in products:
        name = product["product_name"]

        grouped_product = products_by_name.setdefault(
            name,
            {
                "product_name": name,
                "image_url": product["image_url"],
                "product_id": product["product_id"],
                "descriptions": [],
            },
        )
        option = {
            "product_id": product["product_id"],
            "ram": product["ram"],
            "rom": product["rom"],
            "charger_power": product["charger_power"],
            "price": product["price"],
            "stock_quantity": product["stock_quantity"],
        }
        if not any(
            all(
                existing[field] == option[field]
                for field in ("ram", "rom", "charger_power", "price")
            )
            for existing in grouped_product["descriptions"]
        ):
            grouped_product["descriptions"].append(option)

    return render_template(
        "products/list.html",
        store_name="Apple Store",
        category_name=category["category_name"],
        products=list(products_by_name.values()),
        filters=filters,
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
                SELECT product_id, color, ram, rom, charger_power, price, stock_quantity
                FROM Products
                WHERE category_id = ?
                    AND product_name = ?
                    AND is_active = 1
                ORDER BY product_id ASC;
                """,
                (product["category_id"], product["product_name"]),
            )
            variants = rows_to_dicts(cursor)
            for variant in variants:
                if variant["rom"] and not any(
                    option["rom"] == variant["rom"] for option in rom_options
                ):
                    matching_variant = next(
                        (
                            candidate
                            for candidate in variants
                            if candidate["rom"] == variant["rom"]
                            and candidate["color"] == product["color"]
                            and candidate["ram"] == product["ram"]
                            and candidate["charger_power"] == product["charger_power"]
                        ),
                        None,
                    )
                    if matching_variant:
                        rom_options.append(matching_variant)

                if variant["color"] and not any(
                    option["color"] == variant["color"] for option in color_options
                ):
                    matching_variant = next(
                        (
                            candidate
                            for candidate in variants
                            if candidate["color"] == variant["color"]
                            and candidate["rom"] == product["rom"]
                            and candidate["ram"] == product["ram"]
                            and candidate["charger_power"] == product["charger_power"]
                        ),
                        None,
                    )
                    if matching_variant:
                        color_options.append(matching_variant)
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
        supports_engraving=(
            products[0]["category_name"].casefold() in {"ipad", "airpods"}
            or "apple pencil" in products[0]["product_name"].casefold()
        ),
    )

@app.route("/cart")
def cart_page():
    login_redirect = _require_customer_login(
        url_for("cart_page"),
        url_for("home"),
    )
    if login_redirect:
        return login_redirect

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
            SELECT p.product_id, p.product_name, p.color, p.price,
                p.stock_quantity, p.ram, p.rom, img.image_url
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
    available_ids = set()
    for product in products:
        available_ids.add(str(product["product_id"]))
        product["quantity"] = cart.get(str(product["product_id"]), 0)
        product["line_total"] = product["price"] * product["quantity"]
        product["stock_available"] = product["quantity"] <= product["stock_quantity"]
        product["engraving_text"] = session.get("cart_engraving", {}).get(
            str(product["product_id"]), ""
        )
        items.append(product)

    removed_ids = set(cart) - available_ids
    if removed_ids:
        session["cart"] = {
            product_id: quantity
            for product_id, quantity in cart.items()
            if product_id in available_ids
        }
        session["cart_engraving"] = {
            product_id: engraving
            for product_id, engraving in session.get("cart_engraving", {}).items()
            if product_id in available_ids
        }
        flash("Một số sản phẩm không còn khả dụng đã được xóa khỏi giỏ hàng.", "error")

    total = sum((item["line_total"] for item in items), 0)
    can_checkout = all(item["stock_available"] for item in items)
    return render_template(
        "cart/index.html",
        store_name="Apple Store",
        items=items,
        total=total,
        can_checkout=can_checkout,
    )

@app.post("/cart/items/<int:product_id>")
def add_to_cart(product_id):
    login_redirect = _require_customer_login(
        url_for("product_detail", product_id=product_id),
        url_for("home"),
    )
    if login_redirect:
        return login_redirect

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT p.stock_quantity, p.product_name, c.category_name
            FROM Products AS p
            JOIN Categories AS c ON c.category_id = p.category_id
            WHERE p.product_id = ? AND p.is_active = 1;
            """,
            (product_id,),
        )
        product = cursor.fetchone()
        if not product:
            abort(404)
    finally:
        conn.close()

    cart = session.get("cart", {})
    product_key = str(product_id)
    engraving_text = request.form.get("engraving_text", "").strip()
    supports_engraving = (
        product[2].casefold() in {"ipad", "airpods"}
        or "apple pencil" in product[1].casefold()
    )
    if engraving_text and (
        not supports_engraving
        or len(engraving_text.encode("utf-16-le")) // 2 > 30
        or any(ord(character) < 32 for character in engraving_text)
    ):
        abort(400, description="Nội dung khắc không hợp lệ hoặc sản phẩm không hỗ trợ khắc.")
    if product[0] < 1:
        flash("Sản phẩm hiện đã hết hàng.", "error")
        return redirect(url_for("product_detail", product_id=product_id))
    if cart.get(product_key, 0) >= product[0]:
        flash("Số lượng trong giỏ đã đạt tồn kho hiện có.", "error")
        return redirect(url_for("product_detail", product_id=product_id))
    current_engraving = session.get("cart_engraving", {}).get(product_key, "")
    if cart.get(product_key, 0) and current_engraving != engraving_text:
        flash(
            "Mỗi cấu hình sản phẩm chỉ hỗ trợ một nội dung khắc trong mỗi đơn. "
            "Hãy xóa sản phẩm hiện tại trước khi chọn nội dung khác.",
            "error",
        )
        return redirect(url_for("cart_page"))
    cart[product_key] = cart.get(product_key, 0) + 1
    session["cart"] = cart
    if engraving_text:
        engravings = session.get("cart_engraving", {})
        engravings[product_key] = engraving_text
        session["cart_engraving"] = engravings
    flash("Sản phẩm đã được thêm vào giỏ hàng", "success")
    return redirect(url_for("cart_page"))

@app.post("/cart/items/<int:product_id>/remove")
def remove_from_cart(product_id):
    login_redirect = _require_customer_login(
        url_for("cart_page"),
        url_for("home"),
    )
    if login_redirect:
        return login_redirect

    cart = session.get("cart", {})
    product_key = str(product_id)
    cart.pop(product_key, None)
    session["cart"] = cart
    engravings = session.get("cart_engraving", {})
    engravings.pop(product_key, None)
    session["cart_engraving"] = engravings
    return redirect(url_for("cart_page"))


@app.post("/cart/items/<int:product_id>/quantity")
def update_cart_quantity(product_id):
    login_redirect = _require_customer_login(
        url_for("cart_page"),
        url_for("home"),
    )
    if login_redirect:
        return login_redirect

    try:
        quantity = int(request.form.get("quantity", ""))
    except ValueError:
        abort(400, description="Số lượng không hợp lệ.")
    if quantity < 1:
        abort(400, description="Số lượng phải lớn hơn 0.")

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT stock_quantity
            FROM Products
            WHERE product_id = ? AND is_active = 1;
            """,
            (product_id,),
        )
        product = cursor.fetchone()
    finally:
        conn.close()
    if not product:
        abort(404)
    if quantity > product[0]:
        flash("Số lượng vượt quá tồn kho hiện có.", "error")
        return redirect(url_for("cart_page"))

    cart = session.get("cart", {})
    if str(product_id) not in cart:
        abort(404)
    cart[str(product_id)] = quantity
    session["cart"] = cart
    flash("Đã cập nhật số lượng sản phẩm.", "success")
    return redirect(url_for("cart_page"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    login_redirect = _require_customer_login(
        url_for("checkout"),
        url_for("home"),
    )
    if login_redirect:
        return login_redirect

    cart = session.get("cart", {})
    if not cart:
        flash("Giỏ hàng của bạn đang trống.", "error")
        return redirect(url_for("cart_page"))

    product_ids = [int(product_id) for product_id in cart]
    placeholders = ", ".join("?" for _ in product_ids)
    if request.method == "GET":
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"""--sql
                SELECT p.product_id, p.product_name, p.color, p.price,
                    p.stock_quantity
                FROM Products AS p
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
            product["engraving_text"] = session.get("cart_engraving", {}).get(
                str(product["product_id"]), ""
            )
            items.append(product)
        if len(items) != len(cart):
            flash("Một số sản phẩm trong giỏ không còn khả dụng.", "error")
            return redirect(url_for("cart_page"))
        if any(item["quantity"] > item["stock_quantity"] for item in items):
            flash("Tồn kho không đủ cho số lượng đã chọn. Vui lòng cập nhật giỏ hàng.", "error")
            return redirect(url_for("cart_page"))
        return render_template(
            "cart/checkout.html",
            store_name="Apple Store",
            items=items,
            total=sum((item["line_total"] for item in items), 0),
            payment_choices={
                "cod": "Thanh toán khi nhận hàng",
                "bank_transfer": "Chuyển khoản ngân hàng",
                "credit_card": "Thẻ tín dụng quốc tế (nhân viên hướng dẫn)",
                "domestic_card": "Thẻ ATM nội địa (nhân viên hướng dẫn)",
                "momo": "Ví MoMo (nhân viên hướng dẫn)",
                "credit_installment": "Trả góp qua thẻ tín dụng",
                "momo_installment": "Trả góp qua MoMo",
            },
        )

    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()
    shipping_address = request.form.get("shipping_address", "").strip()
    customer_note = request.form.get("note", "").strip()
    payment_choice = request.form.get("payment_method", "")
    payment_method_labels = {
        "cod": "Thanh toán khi nhận hàng",
        "bank_transfer": "Chuyển khoản ngân hàng",
        "credit_card": "Thẻ tín dụng quốc tế (nhân viên hướng dẫn)",
        "domestic_card": "Thẻ ATM nội địa (nhân viên hướng dẫn)",
        "momo": "Ví MoMo (nhân viên hướng dẫn)",
    }
    payment_method = payment_method_labels.get(payment_choice)
    installment_months = request.form.get("installment_months", "")
    allowed_installments = {
        "credit_installment": {"3", "6", "9", "12"},
        "momo_installment": {"6", "12", "18", "24"},
    }
    if payment_choice in allowed_installments:
        if installment_months not in allowed_installments[payment_choice]:
            abort(400, description="Kỳ hạn trả góp không hợp lệ.")
        provider = "thẻ tín dụng" if payment_choice == "credit_installment" else "MoMo"
        payment_method = f"Trả góp {provider} - {installment_months} tháng"
    elif payment_choice not in payment_method_labels:
        abort(400, description="Phương thức thanh toán không hợp lệ.")

    trade_in_requested = request.form.get("trade_in_requested") == "on"
    trade_in_device = request.form.get("trade_in_device", "").strip()
    consultation_requested = request.form.get("consultation_requested") == "on"
    consultation_message = request.form.get("consultation_message", "").strip()
    if (
        not full_name
        or len(full_name) > 100
        or not phone
        or len(phone) > 15
        or not re.fullmatch(r"[0-9+()\- ]+", phone)
        or not 7 <= sum(character.isdigit() for character in phone) <= 15
        or not shipping_address
        or len(shipping_address) > 255
        or len(customer_note) > 255
        or (trade_in_requested and not trade_in_device)
        or len(trade_in_device) > 160
        or len(consultation_message) > 255
    ):
        abort(400, description="Vui lòng nhập thông tin giao hàng hợp lệ.")

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""--sql
            SELECT p.product_id, p.product_name, p.color, p.price,
                p.stock_quantity, ISNULL(reserved.reserved_quantity, 0) AS reserved_quantity
            FROM Products AS p WITH (UPDLOCK, ROWLOCK)
            OUTER APPLY (
                SELECT SUM(d.quantity) AS reserved_quantity
                FROM OrderDetails AS d
                JOIN Orders AS o ON o.order_id = d.order_id
                WHERE d.product_id = p.product_id
                    AND o.stock_committed = 0
                    AND o.order_status <> N'Đã hủy'
            ) AS reserved
            WHERE p.product_id IN ({placeholders}) AND p.is_active = 1;
            """,
            tuple(product_ids),
        )
        products = rows_to_dicts(cursor)
        products_by_id = {str(product["product_id"]): product for product in products}
        if len(products_by_id) != len(cart):
            abort(409, description="Một số sản phẩm không còn khả dụng.")
        if any(
            quantity < 1
            or quantity
            > products_by_id[product_id]["stock_quantity"]
            - products_by_id[product_id]["reserved_quantity"]
            for product_id, quantity in cart.items()
        ):
            abort(409, description="Tồn kho không đủ cho số lượng đã chọn.")

        items = [
            (
                products_by_id[product_id],
                quantity,
                session.get("cart_engraving", {}).get(product_id, ""),
            )
            for product_id, quantity in cart.items()
        ]
        total = sum(
            (product["price"] * quantity for product, quantity, _ in items),
            Decimal("0"),
        )
        order_notes = []
        if customer_note:
            order_notes.append(f"Ghi chú khách hàng: {customer_note}")
        if trade_in_requested:
            order_notes.append(
                "Yêu cầu thẩm định thu cũ đổi mới (chưa trừ vào đơn hàng): "
                f"{trade_in_device}"
            )
        if consultation_requested:
            consultation_note = "Khách hàng yêu cầu tư vấn trực tuyến/gọi lại"
            if consultation_message:
                consultation_note += f": {consultation_message}"
            order_notes.append(consultation_note)
        note = "\n".join(order_notes) or None

        cursor.execute(
            """--sql
            UPDATE Users
            SET full_name = ?, phone = ?, address = ?
            WHERE user_id = ? AND role = 3 AND is_active = 1;
            """,
            (
                full_name,
                phone,
                shipping_address,
                session["customer_user_id"],
            ),
        )
        if cursor.rowcount != 1:
            abort(409, description="Tài khoản khách hàng không còn khả dụng.")

        cursor.execute(
            """--sql
            INSERT INTO Orders (
                user_id, total_amount, payment_method, shipping_address,
                shipping_fee, note, stock_committed
            )
            OUTPUT INSERTED.order_id
            VALUES (?, ?, ?, ?, 0, ?, 0);
            """,
            (
                session["customer_user_id"],
                total,
                payment_method,
                shipping_address,
                note,
            ),
        )
        order_id = cursor.fetchone()[0]
        for product, quantity, engraving_text in items:
            cursor.execute(
                """--sql
                INSERT INTO OrderDetails (
                    order_id, product_id, quantity, unit_price, engraving_text
                )
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    order_id,
                    product["product_id"],
                    quantity,
                    product["price"],
                    engraving_text or None,
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    session.pop("cart", None)
    session.pop("cart_engraving", None)
    receipt_token = order_receipt_serializer.dumps({"order_id": order_id})
    flash("Đặt hàng thành công! Hóa đơn của bạn đã sẵn sàng để in.", "success")
    return redirect(
        url_for(
            "order_confirmation",
            order_id=order_id,
            receipt_token=receipt_token,
        )
    )


@app.route("/orders/<int:order_id>/confirmation/<receipt_token>")
def order_confirmation(order_id, receipt_token):
    try:
        receipt_data = order_receipt_serializer.loads(receipt_token)
    except BadSignature:
        abort(404)
    if receipt_data.get("order_id") != order_id:
        abort(404)

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT o.order_id, o.order_date, o.total_amount, o.payment_method,
                o.payment_status, o.shipping_address, o.shipping_fee,
                o.order_status, o.note, u.full_name, u.phone
            FROM Orders AS o
            JOIN Users AS u ON u.user_id = o.user_id
            WHERE o.order_id = ?;
            """,
            (order_id,),
        )
        order_rows = rows_to_dicts(cursor)
        if not order_rows:
            abort(404)
        cursor.execute(
            """--sql
            SELECT p.product_name, p.color, d.quantity, d.unit_price,
                d.engraving_text, d.quantity * d.unit_price AS line_total
            FROM OrderDetails AS d
            JOIN Products AS p ON p.product_id = d.product_id
            WHERE d.order_id = ?
            ORDER BY p.product_name ASC;
            """,
            (order_id,),
        )
        items = rows_to_dicts(cursor)
    finally:
        conn.close()

    return render_template(
        "orders/confirmation.html",
        store_name="Apple Store",
        order=order_rows[0],
        items=items,
        home_url=url_for("home"),
    )

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
            and user[3] in (1, 2, 3)
            and user[4]
            and check_password_hash(user[2], password)
        ):
            session.pop("csrf_token", None)
            session.pop("admin_user_id", None)
            session.pop("sales_staff_id", None)
            session.pop("customer_user_id", None)
            session.permanent = False
            next_url = request.args.get("next", "")
            parsed_next_url = urlsplit(next_url)
            safe_next_url = (
                next_url.startswith("/")
                and not next_url.startswith("//")
                and "\\" not in next_url
                and not parsed_next_url.netloc
                and not parsed_next_url.scheme
            )
            if user[3] == 3:
                session["customer_user_id"] = user[0]
                flash("Đăng nhập thành công. Bạn có thể tiếp tục mua sắm.", "success")
                session.pop("login_next", None)
                if safe_next_url and (
                    next_url == url_for("cart_page")
                    or next_url == url_for("checkout")
                    or re.fullmatch(r"/products/\d+", next_url)
                ):
                    return redirect(next_url)
                return redirect(url_for("home"))

            session["admin_user_id" if user[3] == 1 else "sales_staff_id"] = user[0]
            if user[3] == 2:
                if safe_next_url and (
                    next_url == "/staff" or next_url.startswith("/staff/")
                ):
                    return redirect(next_url)
                return redirect(url_for("sales.dashboard"))
            if safe_next_url:
                return redirect(next_url)
            return redirect(url_for("admin.dashboard"))

        flash(
            "Tên đăng nhập hoặc mật khẩu không hợp lệ, hoặc tài khoản chưa được kích hoạt.",
            "error",
        )

    return render_template(
        "auth/login.html",
        store_name="Apple Store",
        csrf_token=session.get("csrf_token", ""),
    )

@app.post("/logout")
def logout():
    session.pop("admin_user_id", None)
    session.pop("sales_staff_id", None)
    session.pop("customer_user_id", None)
    session.pop("login_next", None)
    session.pop("csrf_token", None)
    flash("Bạn đã đăng xuất.", "success")
    return redirect(url_for("login"))


@app.post("/logout-on-close")
def logout_on_close():
    session.clear()
    return "", 204


def _load_customer_profile():
    customer_id = session.get("customer_user_id")
    if customer_id is None:
        return None

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT user_id, full_name, phone, email, address, username
            FROM Users
            WHERE user_id = ? AND role = 3 AND is_active = 1;
            """,
            (customer_id,),
        )
        row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        session.pop("customer_user_id", None)
        return None

    return {
        "user_id": row[0],
        "full_name": row[1],
        "phone": row[2],
        "email": row[3],
        "address": row[4],
        "username": row[5],
    }


@app.get("/account")
def customer_account():
    customer = _load_customer_profile()
    if not customer:
        flash("Vui lòng đăng nhập để xem thông tin tài khoản.", "error")
        return redirect(url_for("login"))

    return render_template(
        "account/profile.html",
        store_name="Apple Store",
        customer=customer,
    )


@app.get("/account/orders")
def customer_orders():
    customer_id = session.get("customer_user_id")
    if customer_id is None:
        flash("Vui lòng đăng nhập để theo dõi đơn hàng.", "error")
        return redirect(url_for("login"))

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT o.order_id, o.order_date, o.total_amount, o.order_status,
                o.payment_status, o.shipping_address, d.product_id,
                p.product_name, p.color, p.ram, p.rom, p.charger_power,
                d.quantity, d.unit_price, d.engraving_text,
                d.quantity * d.unit_price AS line_total
            FROM Orders AS o
            LEFT JOIN OrderDetails AS d ON d.order_id = o.order_id
            LEFT JOIN Products AS p ON p.product_id = d.product_id
            WHERE o.user_id = ?
            ORDER BY o.order_date DESC, o.order_id DESC, p.product_name ASC;
            """,
            (customer_id,),
        )
        order_rows = rows_to_dicts(cursor)
    finally:
        conn.close()

    orders_by_id = {}
    for row in order_rows:
        order = orders_by_id.setdefault(
            row["order_id"],
            {
                "order_id": row["order_id"],
                "order_date": row["order_date"],
                "total_amount": row["total_amount"],
                "order_status": row["order_status"],
                "payment_status": row["payment_status"],
                "shipping_address": row["shipping_address"],
                "items": [],
            },
        )
        if row["product_id"] is not None:
            order["items"].append(
                {
                    "product_name": row["product_name"],
                    "color": row["color"],
                    "ram": row["ram"],
                    "rom": row["rom"],
                    "charger_power": row["charger_power"],
                    "quantity": row["quantity"],
                    "unit_price": row["unit_price"],
                    "engraving_text": row["engraving_text"],
                    "line_total": row["line_total"],
                }
            )

    return render_template(
        "account/orders.html",
        store_name="Apple Store",
        orders=list(orders_by_id.values()),
    )


@app.route("/account/edit", methods=["GET", "POST"])
def edit_customer_account():
    customer = _load_customer_profile()
    if not customer:
        flash("Vui lòng đăng nhập để chỉnh sửa tài khoản.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip() or None
        email = request.form.get("email", "").strip() or None
        address = request.form.get("address", "").strip() or None
        customer.update(
            full_name=full_name,
            phone=phone,
            email=email,
            address=address,
        )

        if (
            not full_name
            or len(full_name) > 100
            or (phone and (
                len(phone) > 15
                or not re.fullmatch(r"[0-9+()\- ]+", phone)
                or not 7 <= sum(character.isdigit() for character in phone) <= 15
            ))
            or (email and (
                len(email) > 100
                or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
            ))
            or (address and len(address) > 255)
        ):
            flash("Vui lòng kiểm tra lại thông tin cá nhân.", "error")
            return render_template(
                "account/edit.html",
                store_name="Apple Store",
                customer=customer,
            )

        conn = get_connection()
        try:
            cursor = conn.cursor()
            if email:
                cursor.execute(
                    """--sql
                    SELECT user_id FROM Users
                    WHERE email = ? AND user_id <> ?;
                    """,
                    (email, customer["user_id"]),
                )
                if cursor.fetchone():
                    flash("Email này đã được sử dụng bởi tài khoản khác.", "error")
                    return render_template(
                        "account/edit.html",
                        store_name="Apple Store",
                        customer=customer,
                    )

            cursor.execute(
                """--sql
                UPDATE Users
                SET full_name = ?, phone = ?, email = ?, address = ?
                WHERE user_id = ? AND role = 3 AND is_active = 1;
                """,
                (
                    full_name,
                    phone,
                    email,
                    address,
                    customer["user_id"],
                ),
            )
            if cursor.rowcount != 1:
                abort(409, description="Tài khoản khách hàng không còn khả dụng.")
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        flash("Thông tin cá nhân đã được cập nhật.", "success")
        return redirect(url_for("customer_account"))

    return render_template(
        "account/edit.html",
        store_name="Apple Store",
        customer=customer,
    )


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


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip() or None
        address = request.form.get("address", "").strip() or None
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if (
            not full_name
            or len(full_name) > 100
            or not username
            or len(username) > 50
            or (phone and (
                len(phone) > 15
                or not re.fullmatch(r"[0-9+()\- ]+", phone)
                or not 7 <= sum(character.isdigit() for character in phone) <= 15
            ))
            or (email and (
                len(email) > 100
                or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
            ))
            or (address and len(address) > 255)
            or len(password) < 8
            or password != confirm_password
        ):
            flash("Vui lòng kiểm tra lại thông tin đăng ký.", "error")
            return render_template(
                "auth/register.html",
                store_name="Apple Store",
                csrf_token=session.get("csrf_token", ""),
            )

        conn = get_connection()
        try:
            cursor = conn.cursor()
            if email:
                cursor.execute(
                    """--sql
                    SELECT user_id FROM Users
                    WHERE username = ? OR email = ?;
                    """,
                    (username, email),
                )
            else:
                cursor.execute(
                    "SELECT user_id FROM Users WHERE username = ?;",
                    (username,),
                )
            if cursor.fetchone():
                flash("Tên đăng nhập hoặc email đã được sử dụng.", "error")
                return render_template(
                    "auth/register.html",
                    store_name="Apple Store",
                    csrf_token=session.get("csrf_token", ""),
                )

            cursor.execute(
                """--sql
                INSERT INTO Users (
                    full_name, phone, email, address, username, password_hash,
                    role, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, 3, 1);
                """,
                (
                    full_name,
                    phone or None,
                    email,
                    address,
                    username,
                    generate_password_hash(password),
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        flash("Đăng ký thành công. Vui lòng đăng nhập để tiếp tục.", "success")
        return redirect(url_for("login"))

    return render_template(
        "auth/register.html",
        store_name="Apple Store",
        csrf_token=session.get("csrf_token", ""),
    )


if __name__ == "__main__":
    app.run(debug=True)