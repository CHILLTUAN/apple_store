import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SERVER = os.getenv("DB_SERVER")
DATABASE = os.getenv("DB_NAME")
DRIVER = os.getenv("DB_DRIVER")

def get_connection():
    if not SERVER or not DATABASE or not DRIVER:
        raise ValueError(
            "Thiếu cấu hình database. "
            "Vui lòng kiểm tra file .env."
        )

    connection_string = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={SERVER};"
        f"DATABASE={DATABASE};"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

    return pyodbc.connect(connection_string)