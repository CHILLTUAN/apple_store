from database.connection import get_connection
from database.utils import rows_to_dicts 

def get_categories():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""--sql
            SELECT category_id, 
                category_name, 
                slug, 
                image_url
            FROM Categories
            WHERE is_active = 1
            ORDER BY category_id ASC;
        """)

        categories = rows_to_dicts(cursor)
        
    finally:
        conn.close()
    return categories
