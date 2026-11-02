from werkzeug.security import generate_password_hash
from database.connection import get_connection

conn = get_connection()
try:
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM dbo.Users WHERE username = ?;", ("ADMIN",))

    if cursor.fetchone():
        raise ValueError("Username ADMIN already exists.")

    cursor.execute(
        """
        INSERT INTO dbo.Users (full_name, username, password_hash, role, is_active)
        VALUES (?, ?, ?, 1, 1);
        """,
        ("Administrator", "ADMIN", generate_password_hash("12345678")),
    )
    conn.commit()
finally:
    conn.close()

print("Created active administrator account: ADMIN")