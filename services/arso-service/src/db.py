from datetime import datetime

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import os

DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'postgres'),
    'user': os.getenv('DB_USER', 'main'),
    'password': os.getenv('DB_PASSWORD', 'QJpwX53lar404!')
}

def get_connection():
    """Create and return a database connection."""
    return psycopg2.connect(**DATABASE_CONFIG)


def get_active_events(areas: list, now: datetime):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)


    try:
        if len(areas) == 1:
            query = """
                SELECT * FROM alert_info
                  WHERE area = %s
                  AND expires >= %s
            """
            params = [areas[0], now, now]

        else:
            placeholders = ",".join(["%s"] * len(areas))
            query = f"""
                SELECT * FROM alert_info
                  WHERE area IN ({placeholders})
                  AND expires >= %s
            """
            params = areas + [now, now]

        cursor.execute(sql.SQL(query), params)
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving events: {e}")
        return []
    finally:
        cursor.close()
        conn.close()