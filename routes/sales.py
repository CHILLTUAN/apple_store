import hmac
import secrets
from datetime import date

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

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
)
from database.utils import rows_to_dicts
from routes.admin import (
    _categories,
    ORDER_STATUSES,
    _product_categories,
    _product_form_data,
    _save_product_image,
)


sales_bp = Blueprint("sales", __name__, url_prefix="/staff")


@sales_bp.before_request
def load_sales_staff():
    user_id = session.get("sales_staff_id")
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

    if not user or user[3] != 2 or not user[4]:
        session.pop("sales_staff_id", None)
        flash("Tài khoản không còn quyền truy cập trang nhân viên.", "error")
        return redirect(url_for("login"))

    g.sales_staff = {
        "user_id": user[0],
        "full_name": user[1],
        "username": user[2],
    }
    session.setdefault("csrf_token", secrets.token_urlsafe(32))
    if request.method == "POST" and not hmac.compare_digest(
        session["csrf_token"], request.form.get("csrf_token", "")
    ):
        abort(400, description="Yêu cầu không hợp lệ hoặc đã hết hạn.")


@sales_bp.app_context_processor
def provide_sales_csrf_token():
    return {"csrf_token": session.get("csrf_token", "")}


def _date_range(default_to_today=False):
    start_text = request.args.get("from_date", "").strip()
    end_text = request.args.get("to_date", "").strip()
    if default_to_today:
        today = date.today()
        start_text = start_text or today.replace(day=1).isoformat()
        end_text = end_text or today.isoformat()

    try:
        start_date = date.fromisoformat(start_text) if start_text else None
        end_date = date.fromisoformat(end_text) if end_text else None
    except ValueError:
        abort(400, description="Ngày lọc không hợp lệ.")
    if start_date and end_date and start_date > end_date:
        abort(400, description="Ngày bắt đầu không được sau ngày kết thúc.")
    return start_text, end_text


@sales_bp.route("/")
def dashboard():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT
                (SELECT COUNT(*) FROM Orders WHERE order_status = N'Chờ duyệt')
                    AS pending_orders,
                (SELECT COUNT(*) FROM Orders
                    WHERE order_status <> N'Đã hủy'
                    AND CAST(order_date AS DATE) = CAST(GETDATE() AS DATE))
                    AS orders_today,
                (SELECT ISNULL(SUM(total_amount), 0) FROM Orders
                    WHERE order_status <> N'Đã hủy'
                    AND CAST(order_date AS DATE) = CAST(GETDATE() AS DATE))
                    AS revenue_today,
                (SELECT ISNULL(SUM(total_amount), 0) FROM Orders
                    WHERE order_status <> N'Đã hủy'
                    AND YEAR(order_date) = YEAR(GETDATE())
                    AND MONTH(order_date) = MONTH(GETDATE()))
                    AS revenue_month;
            """
        )
        stats = rows_to_dicts(cursor)[0]
        cursor.execute(
            """--sql
            SELECT TOP 8 o.order_id, u.full_name, o.order_date,
                o.total_amount, o.order_status
            FROM Orders AS o
            JOIN Users AS u ON u.user_id = o.user_id
            WHERE o.order_status <> N'Đã hủy'
            ORDER BY o.order_date DESC, o.order_id DESC;
            """
        )
        recent_orders = rows_to_dicts(cursor)
    finally:
        conn.close()

    return render_template(
        "staff/dashboard.html",
        title="Tổng quan bán hàng",
        stats=stats,
        recent_orders=recent_orders,
        active_nav="dashboard",
    )


@sales_bp.route("/orders")
def orders():
    search = request.args.get("q", "").strip()
    start_date, end_date = _date_range()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT TOP 250 o.order_id, u.full_name, u.phone, o.order_date,
                o.total_amount, o.payment_method, o.shipping_address,
                o.order_status
            FROM Orders AS o
            JOIN Users AS u ON u.user_id = o.user_id
            WHERE (? = N'' OR u.full_name LIKE N'%' + ? + N'%'
                OR CONVERT(NVARCHAR(20), o.order_id) LIKE N'%' + ? + N'%')
                AND o.order_status <> N'Đã hủy'
                AND (? = N'' OR o.order_date >= CAST(? AS DATE))
                AND (? = N'' OR o.order_date < DATEADD(DAY, 1, CAST(? AS DATE)))
            ORDER BY o.order_date DESC, o.order_id DESC;
            """,
            (
                search, search, search,
                start_date, start_date,
                end_date, end_date,
            ),
        )
        order_rows = rows_to_dicts(cursor)
    finally:
        conn.close()
    return render_template(
        "staff/orders.html",
        title="Đơn hàng",
        orders=order_rows,
        statuses=ORDER_STATUSES,
        status_options=ORDER_STATUS_OPTIONS,
        search=search,
        from_date=start_date,
        to_date=end_date,
        active_nav="orders",
    )


@sales_bp.route("/orders/<int:order_id>/invoice")
def order_invoice(order_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT o.order_id, o.order_date, o.total_amount, o.payment_method,
                o.payment_status, o.shipping_address, o.shipping_fee,
                o.order_status, o.note, u.full_name, u.phone, u.email
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
        "staff/invoice.html",
        title=f"Hóa đơn #{order_id}",
        order=order_rows[0],
        items=items,
        active_nav="orders",
    )


@sales_bp.post("/orders/<int:order_id>/status")
def update_status(order_id):
    status = request.form.get("order_status", "")
    if status not in ORDER_STATUSES:
        abort(400, description="Trạng thái đơn hàng không hợp lệ.")
    conn = get_connection()
    transition_error = None
    try:
        cursor = conn.cursor()
        update_order_status(cursor, order_id, status)
        conn.commit()
    except OrderNotFoundError:
        conn.rollback()
        abort(404)
    except OrderStatusTransitionError as error:
        conn.rollback()
        transition_error = str(error)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    if transition_error:
        flash(transition_error, "error")
    elif status == "Đã hủy":
        flash("Đơn hàng đã được hủy", "success")
    else:
        flash("Đã cập nhật trạng thái đơn hàng.", "success")
    return redirect(url_for("sales.orders"))


@sales_bp.route("/products")
def products():
    search = request.args.get("q", "").strip()
    return render_template(
        "staff/products.html",
        title="Sản phẩm",
        products=get_admin_products(search, include_all=True),
        search=search,
        active_nav="products",
    )


@sales_bp.route("/categories")
def categories():
    return render_template(
        "staff/categories.html",
        title="Danh mục",
        category_rows=_categories(),
        active_nav="categories",
    )


@sales_bp.route("/categories/new", methods=["GET", "POST"])
@sales_bp.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
def edit_category(category_id=None):
    category = None
    if category_id is not None:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """--sql
                SELECT category_id, category_name, slug, image_url, is_active
                FROM Categories
                WHERE category_id = ?;
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
                    """--sql
                    SELECT category_id
                    FROM Categories
                    WHERE slug = ? AND category_id <> ?;
                    """,
                    (slug, category_id or 0),
                )
                if cursor.fetchone():
                    flash("Slug này đã được sử dụng.", "error")
                else:
                    if category_id is None:
                        cursor.execute(
                            """--sql
                            INSERT INTO Categories (
                                category_name, slug, image_url, is_active
                            )
                            VALUES (?, ?, ?, ?);
                            """,
                            (name, slug, image_url, is_active),
                        )
                    else:
                        cursor.execute(
                            """--sql
                            UPDATE Categories
                            SET category_name = ?, slug = ?, image_url = ?,
                                is_active = ?
                            WHERE category_id = ?;
                            """,
                            (name, slug, image_url, is_active, category_id),
                        )
                    conn.commit()
                    flash("Đã lưu danh mục.", "success")
                    return redirect(url_for("sales.categories"))
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    return render_template(
        "staff/category_form.html",
        title="Thêm danh mục" if category_id is None else "Chỉnh sửa danh mục",
        category=category,
        active_nav="categories",
    )


@sales_bp.route("/products/new", methods=["GET", "POST"])
def new_product():
    if request.method == "POST":
        try:
            data = _product_form_data(request.form)
            if not data[1]:
                raise ValueError("Vui lòng nhập tên sản phẩm.")
            if not any(
                category["category_id"] == data[0]
                for category in _product_categories()
            ):
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
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            flash("Đã thêm sản phẩm.", "success")
            return redirect(url_for("sales.products"))

    return render_template(
        "staff/product_form.html",
        title="Thêm sản phẩm",
        product=None,
        categories=_product_categories(),
        active_nav="products",
    )


@sales_bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
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
            if not any(
                category["category_id"] == data[0]
                for category in _product_categories()
            ):
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
                    SET category_id = ?, product_name = ?, color = ?,
                        description = ?, price = ?, stock_quantity = ?,
                        ram = ?, rom = ?, charger_power = ?
                    WHERE product_id = ?;
                    """,
                    (*data[:9], product_id),
                )
                _save_product_image(cursor, product_id, data[9])
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            flash("Đã cập nhật sản phẩm.", "success")
            return redirect(url_for("sales.products"))

    return render_template(
        "staff/product_form.html",
        title="Chỉnh sửa sản phẩm",
        product=product,
        categories=_product_categories(),
        active_nav="products",
    )


@sales_bp.post("/products/<int:product_id>/delete")
def delete_product(product_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT product_id FROM Products WITH (UPDLOCK, HOLDLOCK) WHERE product_id = ?;",
            (product_id,),
        )
        if not cursor.fetchone():
            abort(404)

        cursor.execute(
            """--sql
            SELECT TOP 1 order_id
            FROM OrderDetails WITH (UPDLOCK, HOLDLOCK)
            WHERE product_id = ?;
            """,
            (product_id,),
        )
        if cursor.fetchone():
            conn.rollback()
            flash(
                "Không thể xóa sản phẩm đã có trong đơn hàng. Bạn có thể ẩn sản phẩm.",
                "error",
            )
            return redirect(url_for("sales.products", q=request.args.get("q") or None))

        cursor.execute("DELETE FROM ProductImages WHERE product_id = ?;", (product_id,))
        cursor.execute("DELETE FROM Products WHERE product_id = ?;", (product_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    flash("Đã xóa sản phẩm.", "success")
    return redirect(url_for("sales.products", q=request.args.get("q") or None))


@sales_bp.post("/products/<int:product_id>/visibility")
def set_product_visibility(product_id):
    desired_state = request.form.get("is_active")
    if desired_state not in {"0", "1"}:
        abort(400, description="Trạng thái hiển thị sản phẩm không hợp lệ.")

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Products SET is_active = ? WHERE product_id = ?;",
            (int(desired_state), product_id),
        )
        if cursor.rowcount == 0:
            abort(404)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    flash(
        "Đã hiển thị sản phẩm trên cửa hàng."
        if desired_state == "1"
        else "Đã ẩn sản phẩm khỏi cửa hàng.",
        "success",
    )
    return redirect(url_for("sales.products", q=request.args.get("q") or None))


@sales_bp.route("/reports")
def reports():
    start_date, end_date = _date_range(default_to_today=True)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """--sql
            SELECT COUNT(*) AS order_count,
                ISNULL(SUM(total_amount), 0) AS revenue
            FROM Orders
            WHERE order_status <> N'Đã hủy'
                AND order_date >= CAST(? AS DATE)
                AND order_date < DATEADD(DAY, 1, CAST(? AS DATE));
            """,
            (start_date, end_date),
        )
        totals = rows_to_dicts(cursor)[0]
        cursor.execute(
            """--sql
            SELECT p.product_name, SUM(d.quantity) AS quantity_sold,
                SUM(d.quantity * d.unit_price) AS revenue
            FROM Orders AS o
            JOIN OrderDetails AS d ON d.order_id = o.order_id
            JOIN Products AS p ON p.product_id = d.product_id
            WHERE o.order_status <> N'Đã hủy'
                AND o.order_date >= CAST(? AS DATE)
                AND o.order_date < DATEADD(DAY, 1, CAST(? AS DATE))
            GROUP BY p.product_name
            ORDER BY revenue DESC, p.product_name ASC;
            """,
            (start_date, end_date),
        )
        product_sales = rows_to_dicts(cursor)
    finally:
        conn.close()
    return render_template(
        "staff/reports.html",
        title="Báo cáo bán hàng",
        totals=totals,
        product_sales=product_sales,
        from_date=start_date,
        to_date=end_date,
        active_nav="reports",
    )


@sales_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        try:
            product_limit = int(request.form.get("homepage_products_per_category", ""))
        except ValueError:
            flash("Số sản phẩm phải là số nguyên.", "error")
            return redirect(url_for("sales.settings"))

        if not 1 <= product_limit <= MAX_HOME_PRODUCTS_PER_CATEGORY:
            flash(
                f"Số sản phẩm phải nằm trong khoảng 1 đến {MAX_HOME_PRODUCTS_PER_CATEGORY}.",
                "error",
            )
            return redirect(url_for("sales.settings"))

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
        return redirect(url_for("sales.settings"))

    return render_template(
        "staff/settings.html",
        title="Cài đặt hệ thống",
        homepage_products_per_category=get_home_product_limit(),
        max_home_products_per_category=MAX_HOME_PRODUCTS_PER_CATEGORY,
        active_nav="settings",
    )
