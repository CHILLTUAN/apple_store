import pyodbc

def get_connection():
    return pyodbc.connect(
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=QThai\\SQLEXPRESS;"
        "DATABASE=APPLESTORE;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )