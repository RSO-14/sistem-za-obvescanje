from datetime import datetime

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import os

DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def get_connection():
    """Create and return a database connection."""
    return psycopg2.connect(**DATABASE_CONFIG)


def get_active_events(areas: list):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)


    try:
        if len(areas) == 1:
            query = """
                SELECT * FROM alert_info
                  WHERE area = %s
                  AND expires >= NOW()
            """
            params = [areas[0]]

        else:
            placeholders = ",".join(["%s"] * len(areas))
            query = f"""
                SELECT * FROM alert_info
                  WHERE area IN ({placeholders})
                  AND expires >= NOW()
            """
            params = areas

        cursor.execute(sql.SQL(query), params)
        return cursor.fetchall()

    except Exception as e:
        print(f"Error retrieving events: {e}")
        return []
    finally:
        cursor.close()
        conn.close()