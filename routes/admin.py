import hmac
import secrets
from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from database.connection import get_connection
from database.order_repository import (
    OrderNotFoundError,
    ORDER_STATUS_OPTIONS,
    OrderStatusTransitionError,
    update_order_status,
)
from database.product_repository import (
    MAX_HOME_PRODUCTS_PER_CATEGORY,
    get_admin_products,
    get_home_product_limit,
    get_home_products,
)
from database.utils import rows_to_dicts


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
ORDER_STATUSES = ("Chờ duyệt", "Đang chuẩn bị", "Đang giao", "Đã giao", "Đã hủy")


@admin_bp.before_request
def load_admin():
    user_id = session.get("admin_user_id")
    if not user_id:
        return redirect(url_for("login", next=request.full_path))

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT user_id, full_name, username, role, is_active
            FROM Users
            WHERE user_id = ?;
            """,
            (user_id,),
        )
        user = cursor.fetchone()
    finally:
        conn.close()

    if not user or user[3] != 1 or not user[4]:
        session.pop("admin_user_id", None)
        flash("Tài khoản không còn quyền truy cập trang quản trị.", "error")
        return redirect(url_for("login"))

    g.admin_user = {
        "user_id": user[0],
        "full_name": user[1],
        "username": user[2],
    }
    session.setdefault("csrf_token", secrets.token_urlsafe(32))
    if request.method == "POST" and not hmac.compare_digest(
        session["csrf_token"], request.form.get("csrf_token", "")
    ):
        abort(400, description="Yêu cầu không hợp lệ hoặc đã hết hạn.")


@admin_bp.app_context_processor
def provide_csrf_token():
    return {"csrf_token": session.get("csrf_token", "")}


def _categories(active_only=False):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT category_id, category_name, slug, image_url, is_active
            FROM Categories
            WHERE (? = 0 OR is_active = 1)
            ORDER BY category_name ASC;
            """,
            (0 if not active_only else 1,),
        )
        return rows_to_dicts(cursor)
    finally:
        conn.close()


def _save_product_image(cursor, product_id, image_url):
    if not image_url:
        return
    cursor.execute(
        "SELECT TOP 1 image_id FROM ProductImages WHERE product_id = ? AND is_primary = 1;",
        (product_id,),
    )
    existing_image = cursor.fetchone()
    if existing_image:
        cursor.execute(
            "UPDATE ProductImages SET image_url = ? WHERE image_id = ?;",
            (image_url, existing_image[0]),
        )
    else:
        cursor.execute(
            """--sql
            INSERT INTO ProductImages (product_id, image_url, is_primary)
            VALUES (?, ?, 1);
            """,
            (product_id, image_url),
        )


def _product_form_data(form):
    try:
        category_id = int(form.get("category_id", ""))
        price = Decimal(form.get("price", ""))
        stock_quantity = int(form.get("stock_quantity", ""))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Danh mục, giá bán hoặc số lượng tồn kho không hợp lệ.")

    if not price.is_finite() or price > Decimal("9999999999999999.99"):
        raise ValueError("Giá bán vượt quá giới hạn cho phép.")
    if price < 0 or stock_quantity < 0:
        raise ValueError("Giá bán và số lượng tồn kho không được âm.")

    return (
        category_id,
        form.get("product_name", "").strip(),
        form.get("color", "").strip() or None,
        form.get("description", "").strip() or None,
        price,
        stock_quantity,
        form.get("ram", "").strip() or None,
        form.get("rom", "").strip() or None,
        form.get("charger_power", "").strip() or None,
        form.get("image_url", "").strip(),
    )


def _product_categories():
    return [category for category in _categories() if category["is_active"]]


@admin_bp.route("/")
def dashboard():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT
                (SELECT COUNT(*) FROM Orders WHERE order_status <> N'Đã hủy') AS total_orders,
                (SELECT COUNT(*) FROM Users WHERE role = 3 AND is_active = 1) AS customers,
                (SELECT COUNT(*) FROM Orders WHERE order_status = N'Chờ duyệt') AS pending_orders,
                (SELECT ISNULL(SUM(total_amount), 0) FROM Orders
                    WHERE order_status <> N'Đã hủy'
                    AND CAST(order_date AS DATE) = CAST(GETDATE() AS DATE)) AS revenue_today,
                (SELECT ISNULL(SUM(total_amount), 0) FROM Orders
                    WHERE order_status <> N'Đã hủy'
                    AND YEAR(order_date) = YEAR(GETDATE())
                    AND MONTH(order_date) = MONTH(GETDATE())) AS revenue_month,
                (SELECT ISNULL(SUM(total_amount), 0) FROM Orders
                    WHERE order_status <> N'Đã hủy'
                    AND YEAR(order_date) = YEAR(GETDATE())) AS revenue_year;
            """
        )
        stats = rows_to_dicts(cursor)[0]
        storefront_product_count = len(get_home_products())
        cursor.execute(
            """--sql
            SELECT TOP 8 o.order_id, u.full_name, o.order_date, o.total_amount,
                o.order_status, o.payment_method
            FROM Orders AS o
            JOIN Users AS u ON u.user_id = o.user_id
            ORDER BY o.order_date DESC, o.order_id DESC;
            """
        )
        recent_orders = rows_to_dicts(cursor)
        cursor.execute(
            """--sql
            SELECT
                DATEFROMPARTS(YEAR(order_date), MONTH(order_date), 1) AS month_start,
                SUM(total_amount) AS revenue
            FROM Orders
            WHERE order_status <> N'Đã hủy'
                AND order_date >= DATEADD(
                    MONTH, -5, DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
                )
            GROUP BY DATEFROMPARTS(YEAR(order_date), MONTH(order_date), 1)
            ORDER BY month_start ASC;
            """
        )
        monthly_revenue = rows_to_dicts(cursor)
        for month in monthly_revenue:
            month["month_label"] = (
                f"Tháng {month['month_start'].month}/{month['month_start'].year}"
            )
    finally:
        conn.close()

    return render_template(
        "admin/dashboard.html",
        title="Tổng quan",
        stats=stats,
        storefront_product_count=storefront_product_count,
        recent_orders=recent_orders,
        monthly_revenue=monthly_revenue,
        revenue_max=max((item["revenue"] for item in monthly_revenue), default=0),
        active_nav="dashboard",
    )


@admin_bp.route("/products")
def products():
    search = request.args.get("q", "").strip()
    include_all = request.args.get("all") == "1"
    product_rows = get_admin_products(search, include_all=include_all)
    return render_template(
        "admin/products.html",
        title="Sản phẩm",
        products=product_rows,
        search=search,
        show_all=include_all,
        active_nav="products",
    )


@admin_bp.route("/products/new", methods=["GET", "POST"])
def new_product():
    if request.method == "POST":
        try:
            data = _product_form_data(request.form)
            if not data[1]:
                raise ValueError("Vui lòng nhập tên sản phẩm.")
            if not any(category["category_id"] == data[0] for category in _product_categories()):
                raise ValueError("Danh mục đã chọn không tồn tại hoặc đang bị ẩn.")
        except ValueError as error:
            flash(str(error), "error")
        else:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """--sql
                    INSERT INTO Products (
                        category_id, product_name, color, description, price,
                        stock_quantity, ram, rom, charger_power
                    )
                    OUTPUT INSERTED.product_id
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    data[:9],
                )
                product_id = cursor.fetchone()[0]
                _save_product_image(cursor, product_id, data[9])
                conn.commit()
            finally:
                conn.close()
            flash("Đã thêm sản phẩm.", "success")
            return redirect(url_for("admin.products"))

    return render_template(
        "admin/product_form.html",
        title="Thêm sản phẩm",
        product=None,
        categories=_product_categories(),
        active_nav="products",
    )


@admin_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT p.*, img.image_url
            FROM Products AS p
            OUTER APPLY (
                SELECT TOP 1 pi.image_url
                FROM ProductImages AS pi
                WHERE pi.product_id = p.product_id
                ORDER BY pi.is_primary DESC, pi.image_id ASC
            ) AS img
            WHERE p.product_id = ?;
            """,
            (product_id,),
        )
        product_rows = rows_to_dicts(cursor)
    finally:
        conn.close()
    if not product_rows:
        abort(404)
    product = product_rows[0]

    if request.method == "POST":
        try:
            data = _product_form_data(request.form)
            if not data[1]:
                raise ValueError("Vui lòng nhập tên sản phẩm.")
            if not any(category["category_id"] == data[0] for category in _product_categories()):
                raise ValueError("Danh mục đã chọn không tồn tại hoặc đang bị ẩn.")
        except ValueError as error:
            flash(str(error), "error")
        else:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """--sql
                    UPDATE Products
                    SET category_id = ?, product_name = ?, color = ?, description = ?,
                        price = ?, stock_quantity = ?, ram = ?, rom = ?, charger_power = ?
                    WHERE product_id = ?;
                    """,
                    (*data[:9], product_id),
                )
                _save_product_image(cursor, product_id, data[9])
                conn.commit()
            finally:
                conn.close()
            flash("Đã cập nhật sản phẩm.", "success")
            return redirect(url_for("admin.products"))

    return render_template(
        "admin/product_form.html",
        title="Chỉnh sửa sản phẩm",
        product=product,
        categories=_product_categories(),
        active_nav="products",
    )


@admin_bp.post("/products/<int:product_id>/delete")
def delete_product(product_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Products SET is_active = 0 WHERE product_id = ?;",
            (product_id,),
        )
        if cursor.rowcount == 0:
            abort(404)
        conn.commit()
    finally:
        conn.close()
    flash("Đã ẩn sản phẩm khỏi cửa hàng.", "success")
    return redirect(url_for("admin.products"))


@admin_bp.route("/categories")
def categories():
    return render_template(
        "admin/categories.html",
        title="Danh mục",
        category_rows=_categories(),
        active_nav="categories",
    )


@admin_bp.route("/categories/new", methods=["GET", "POST"])
@admin_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
def edit_category(category_id=None):
    category = None
    if category_id is not None:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """--sql
                SELECT category_id, category_name, slug, image_url, is_active
                FROM Categories WHERE category_id = ?;
                """,
                (category_id,),
            )
            category_rows = rows_to_dicts(cursor)
        finally:
            conn.close()
        if not category_rows:
            abort(404)
        category = category_rows[0]

    if request.method == "POST":
        name = request.form.get("category_name", "").strip()
        slug = request.form.get("slug", "").strip()
        image_url = request.form.get("image_url", "").strip() or None
        is_active = 1 if request.form.get("is_active") == "1" else 0
        if not name or not slug:
            flash("Tên danh mục và slug không được để trống.", "error")
        else:
            conn = get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT category_id FROM Categories WHERE slug = ? AND category_id <> ?;",
                    (slug, category_id or 0),
                )
                if cursor.fetchone():
                    flash("Slug này đã được sử dụng.", "error")
                else:
                    if category_id is None:
                        cursor.execute(
                            """--sql
                            INSERT INTO Categories (category_name, slug, image_url, is_active)
                            VALUES (?, ?, ?, ?);
                            """,
                            (name, slug, image_url, is_active),
                        )
                    else:
                        cursor.execute(
                            """--sql
                            UPDATE Categories
                            SET category_name = ?, slug = ?, image_url = ?, is_active = ?
                            WHERE category_id = ?;
                            """,
                            (name, slug, image_url, is_active, category_id),
                        )
                    conn.commit()
                    flash("Đã lưu danh mục.", "success")
                    return redirect(url_for("admin.categories"))
            finally:
                conn.close()

    return render_template(
        "admin/category_form.html",
        title="Thêm danh mục" if category_id is None else "Chỉnh sửa danh mục",
        category=category,
        active_nav="categories",
    )


@admin_bp.route("/orders")
def orders():
    search = request.args.get("q", "").strip()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT TOP 250 o.order_id, u.full_name, u.phone, o.order_date,
                o.total_amount, o.payment_method, o.shipping_address, o.order_status
            FROM Orders AS o
            JOIN Users AS u ON u.user_id = o.user_id
            WHERE (? = N'' OR u.full_name LIKE N'%' + ? + N'%'
                OR CONVERT(NVARCHAR(20), o.order_id) LIKE N'%' + ? + N'%')
                AND o.order_status <> N'Đã hủy'
            ORDER BY o.order_date DESC, o.order_id DESC;
            """,
            (search, search, search),
        )
        order_rows = rows_to_dicts(cursor)
    finally:
        conn.close()
    return render_template(
        "admin/orders.html",
        title="Đơn hàng",
        orders=order_rows,
        statuses=ORDER_STATUSES,
        status_options=ORDER_STATUS_OPTIONS,
        search=search,
        active_nav="orders",
    )


@admin_bp.route("/orders/<int:order_id>/invoice")
def order_invoice(order_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT o.order_id, o.order_date, o.total_amount, o.payment_method,
                o.payment_status, o.shipping_address, o.shipping_fee, o.order_status,
                o.note, u.full_name, u.phone, u.email
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
                d.engraving_text,
                d.quantity * d.unit_price AS line_total
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
        "admin/invoice.html",
        title=f"Hóa đơn #{order_id}",
        order=order_rows[0],
        items=items,
        active_nav="orders",
    )


@admin_bp.post("/orders/<int:order_id>/status")
def update_order_status(order_id):
    status = request.form.get("order_status", "")
    if status not in ORDER_STATUSES:
        abort(400, description="Trạng thái đơn hàng không hợp lệ.")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        update_order_status(cursor, order_id, status)
        conn.commit()
    except OrderNotFoundError:
        conn.rollback()
        abort(404)
    except OrderStatusTransitionError as error:
        conn.rollback()
        flash(str(error), "error")
        return redirect(url_for("admin.orders"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if status == "Đã hủy":
        flash("Đơn hàng đã được hủy", "success")
    else:
        flash("Đã cập nhật trạng thái đơn hàng.", "success")
    return redirect(url_for("admin.orders"))


@admin_bp.route("/customers")
def customers():
    return _render_users(role=3, title="Khách hàng", active_nav="customers")


@admin_bp.route("/users")
def users():
    return _render_users(role=None, title="Người dùng", active_nav="users")


def _render_users(role, title, active_nav):
    search = request.args.get("q", "").strip()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT user_id, full_name, phone, email, username, role, is_active, created_at
            FROM Users
            WHERE (? = 0 OR role = ?)
                AND (? = N'' OR full_name LIKE N'%' + ? + N'%'
                    OR username LIKE N'%' + ? + N'%')
            ORDER BY created_at DESC, user_id DESC;
            """,
            (0 if role is None else 1, role or 0, search, search, search),
        )
        user_rows = rows_to_dicts(cursor)
    finally:
        conn.close()
    return render_template(
        "admin/users.html",
        title=title,
        users=user_rows,
        search=search,
        active_nav=active_nav,
    )


@admin_bp.route("/users/new", methods=["GET", "POST"])
def new_user():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        email = request.form.get("email", "").strip() or None
        phone = request.form.get("phone", "").strip() or None
        address = request.form.get("address", "").strip() or None
        try:
            role = int(request.form.get("role", "3"))
            if role not in (1, 2, 3):
                raise ValueError
        except ValueError:
            flash("Vai trò người dùng không hợp lệ.", "error")
        else:
            if not full_name or not username or not password:
                flash("Họ tên, tên đăng nhập và mật khẩu là bắt buộc.", "error")
            elif len(password) < 8:
                flash("Mật khẩu phải có ít nhất 8 ký tự.", "error")
            else:
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT user_id FROM Users WHERE username = ?;",
                        (username,),
                    )
                    if cursor.fetchone():
                        flash("Tên đăng nhập đã tồn tại.", "error")
                    else:
                        cursor.execute(
                            """--sql
                            INSERT INTO Users (
                                full_name, phone, email, address, username,
                                password_hash, role, is_active
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, 1);
                            """,
                            (
                                full_name,
                                phone,
                                email,
                                address,
                                username,
                                generate_password_hash(password),
                                role,
                            ),
                        )
                        conn.commit()
                        flash("Đã thêm người dùng.", "success")
                        return redirect(url_for("admin.users"))
                finally:
                    conn.close()
    return render_template(
        "admin/user_form.html",
        title="Thêm người dùng",
        user=None,
        active_nav="users",
    )


@admin_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def edit_user(user_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT user_id, full_name, phone, email, address, username, role, is_active
            FROM Users WHERE user_id = ?;
            """,
            (user_id,),
        )
        user_rows = rows_to_dicts(cursor)
    finally:
        conn.close()
    if not user_rows:
        abort(404)
    user = user_rows[0]

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip() or None
        phone = request.form.get("phone", "").strip() or None
        address = request.form.get("address", "").strip() or None
        password = request.form.get("password", "")
        is_active = 1 if request.form.get("is_active") == "1" else 0
        try:
            role = int(request.form.get("role", "3"))
            if role not in (1, 2, 3):
                raise ValueError
        except ValueError:
            flash("Vai trò người dùng không hợp lệ.", "error")
        else:
            if not full_name or not username:
                flash("Họ tên và tên đăng nhập là bắt buộc.", "error")
            elif password and len(password) < 8:
                flash("Mật khẩu mới phải có ít nhất 8 ký tự.", "error")
            elif user_id == g.admin_user["user_id"] and (role != 1 or not is_active):
                flash("Không thể gỡ quyền quản trị hoặc khóa tài khoản đang sử dụng.", "error")
            else:
                conn = get_connection()
                try:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT user_id FROM Users WHERE username = ? AND user_id <> ?;",
                        (username, user_id),
                    )
                    if cursor.fetchone():
                        flash("Tên đăng nhập đã tồn tại.", "error")
                    else:
                        if user["role"] == 1 and (role != 1 or not is_active):
                            cursor.execute(
                                """--sql
                                SELECT COUNT(*) FROM Users
                                WHERE role = 1 AND is_active = 1 AND user_id <> ?;
                                """,
                                (user_id,),
                            )
                            if cursor.fetchone()[0] == 0:
                                flash("Không thể khóa hoặc gỡ quyền quản trị viên cuối cùng.", "error")
                                return _render_user_form(user)

                        cursor.execute(
                            """--sql
                            UPDATE Users
                            SET full_name = ?, phone = ?, email = ?, address = ?,
                                username = ?, role = ?, is_active = ?
                            WHERE user_id = ?;
                            """,
                            (full_name, phone, email, address, username, role, is_active, user_id),
                        )
                        if password:
                            cursor.execute(
                                "UPDATE Users SET password_hash = ? WHERE user_id = ?;",
                                (generate_password_hash(password), user_id),
                            )
                        conn.commit()
                        flash("Đã cập nhật người dùng.", "success")
                        return redirect(url_for("admin.users"))
                finally:
                    conn.close()

    return _render_user_form(user)


def _render_user_form(user):
    return render_template(
        "admin/user_form.html",
        title="Chỉnh sửa người dùng",
        user=user,
        active_nav="users",
    )


@admin_bp.route("/revenue")
def revenue():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT TOP 12
                DATEFROMPARTS(YEAR(order_date), MONTH(order_date), 1) AS month_start,
                COUNT(*) AS order_count,
                SUM(total_amount) AS revenue
            FROM Orders
            WHERE order_status <> N'Đã hủy'
                AND order_date >= DATEADD(
                    MONTH, -11, DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
                )
            GROUP BY DATEFROMPARTS(YEAR(order_date), MONTH(order_date), 1)
            ORDER BY month_start DESC;
            """
        )
        monthly_sales = rows_to_dicts(cursor)
    finally:
        conn.close()
    return render_template(
        "admin/revenue.html",
        title="Doanh thu",
        monthly_sales=monthly_sales,
        active_nav="revenue",
    )


@admin_bp.route("/vouchers")
def vouchers():
    return render_template(
        "admin/placeholder.html",
        title="Mã giảm giá",
        description="Cơ sở dữ liệu hiện chưa có bảng mã giảm giá. Hãy bổ sung quy tắc voucher trước khi bật quản lý mã giảm giá.",
        active_nav="vouchers",
    )


@admin_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        try:
            product_limit = int(request.form.get("homepage_products_per_category", ""))
        except ValueError:
            flash("Số sản phẩm phải là số nguyên.", "error")
            return redirect(url_for("admin.settings"))

        if not 1 <= product_limit <= MAX_HOME_PRODUCTS_PER_CATEGORY:
            flash(
                f"Số sản phẩm phải nằm trong khoảng 1 đến {MAX_HOME_PRODUCTS_PER_CATEGORY}.",
                "error",
            )
            return redirect(url_for("admin.settings"))

        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """--sql
                UPDATE StoreSettings
                SET setting_value = ?
                WHERE setting_key = N'homepage_products_per_category';
                """,
                (product_limit,),
            )
            if cursor.rowcount != 1:
                raise RuntimeError(
                    "Không tìm thấy cài đặt số sản phẩm trang chủ. "
                    "Hãy chạy database/sql/homepage_products_setting_migration.sql."
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
        flash("Đã cập nhật số sản phẩm hiển thị trên trang chủ.", "success")
        return redirect(url_for("admin.settings"))

    return render_template(
        "admin/settings.html",
        title="Cài đặt hệ thống",
        homepage_products_per_category=get_home_product_limit(),
        max_home_products_per_category=MAX_HOME_PRODUCTS_PER_CATEGORY,
        active_nav="settings",
    )