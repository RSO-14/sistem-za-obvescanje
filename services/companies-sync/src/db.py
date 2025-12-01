import psycopg2
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
    return psycopg2.connect(**DATABASE_CONFIG)

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("Creating tables...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                organization_id SERIAL PRIMARY KEY,
                organization_name TEXT UNIQUE NOT NULL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization_events (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER REFERENCES organizations(organization_id),
                type TEXT NOT NULL,
                area TEXT NOT NULL,
                headline TEXT NOT NULL,
                description TEXT,
                instruction TEXT,
                effective TIMESTAMPTZ,
                expires TIMESTAMPTZ,
                severity TEXT,
                urgency TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, type, area, headline)
            );
        """)

        conn.commit()
        print("Tables created successfully")
    except Exception as e:
        conn.rollback()
        print(f"Error creating tables: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

def insert_organization(org_name: str):
    print("connecting")
    conn = get_connection()
    cursor = conn.cursor()
    print("done connecting")
    print(org_name)
    try:
        cursor.execute("""
            INSERT INTO organizations (organization_name)
            VALUES (%s)
            ON CONFLICT (organization_name) DO NOTHING;
        """, (org_name,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error inserting organization: {e}")
    finally:
        cursor.close()
        conn.close()

def insert_or_update_event(event: dict):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO organization_events (
                organization_id, type, area, headline, description,
                instruction, effective, expires, severity, urgency
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (organization_id, type, area, headline)
            DO NOTHING
            RETURNING id;
        """, (
            int(event["organization_id"]),
            event["type"],
            event["area"],
            event["headline"],
            event.get("description"),
            event.get("instruction"),
            event.get("effective"),
            event.get("expires"),
            event.get("severity"),
            event.get("urgency")
        ))

        inserted_row = cursor.fetchone()

        if inserted_row:
            conn.commit()
            return True

        cursor.execute("""
            UPDATE organization_events
            SET severity = %s,
                effective = %s,
                description = %s,
                instruction = %s,
                expires = %s,
                urgency = %s
            WHERE organization_id = %s AND type = %s AND area = %s AND headline = %s;
        """, (
            event.get("severity"),
            event.get("effective"),
            event.get("description"),
            event.get("instruction"),
            event.get("expires"),
            event.get("urgency"),
            int(event["organization_id"]),
            event["type"],
            event["area"],
            event["headline"]
        ))

        conn.commit()
        return False

    except Exception as e:
        conn.rollback()
        print(f"Error inserting/updating event: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

def get_organization_id_by_name(org_name: str):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT organization_id FROM organizations WHERE organization_name = %s
        """, (org_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error finding ID for '{org_name}': {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_events(organization_id: int, area=None, effective=None, expires=None, urgency=None):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        query = """
            SELECT * FROM organization_events
            WHERE organization_id = %s
        """
        params = [organization_id]

        if area:
            query += " AND area = %s"
            params.append(area)
        if effective:
            query += " AND effective >= %s"
            params.append(effective)
        if expires:
            query += " AND expires <= %s"
            params.append(expires)
        if urgency:
            query += " AND urgency = %s"
            params.append(urgency)

        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error retrieving events: {e}")
        return []
    finally:
        cursor.close()
        conn.close()
