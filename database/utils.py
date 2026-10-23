def rows_to_dicts(cursor):
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    return [
        dict(zip(columns, row)) 
        for row in rows
    ]