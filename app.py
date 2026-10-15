from flask import Flask, render_template, render_template_string

app = Flask(__name__)

@app.route("/")
def home():
    return render_template(
        "home/index.html",
        store_name="Apple Store",
        message="Flask đã kết nối với HTML thành công!"
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