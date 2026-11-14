import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

SERVER = os.getenv("DB_SERVER")
DATABASE = os.getenv("DB_NAME")
DRIVER = os.getenv("DB_DRIVER")


def get_connection():
    if not all((SERVER, DATABASE, DRIVER)):
        raise ValueError("Thiếu cấu hình database. Vui lòng kiểm tra file .env.")
    return pyodbc.connect(
        f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;"
    )