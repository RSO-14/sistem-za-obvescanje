import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dateutil import parser

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
    clean_name = " ".join(org_name.split())
    try:
        cursor.execute("""
            INSERT INTO organizations (organization_name)
            VALUES (%s)
            ON CONFLICT (organization_name) DO NOTHING;
        """, (clean_name,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error inserting organization: {e}")
    finally:
        cursor.close()
        conn.close()

def norm_datetime(value):
    if value in (None, "", " "):
        return None
    if isinstance(value, str):
        return parser.parse(value)
    return value

def norm_text(value):
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value.strip()

def norm(val):
    if val is None:
        return None
    if isinstance(val, str):
        val = val.strip()
        return val if val else None
    return val

def insert_or_update_event(event: dict):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # TRY INSERT
        cursor.execute("""
            INSERT INTO organization_events (
                organization_id, type, area, headline, description,
                instruction, effective, expires, severity, urgency
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (organization_id, type, area, headline)
            DO NOTHING
            RETURNING id;
        """, (
            event["organization_id"],
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

        inserted = cursor.fetchone()
        if inserted:
            conn.commit()
            return "inserted"

        # FETCH EXISTING
        cursor.execute("""
            SELECT description, instruction, effective, expires, severity, urgency
            FROM organization_events
            WHERE organization_id = %s
              AND type = %s
              AND area = %s
              AND headline = %s;
        """, (
            event["organization_id"],
            event["type"],
            event["area"],
            event["headline"]
        ))

        existing = cursor.fetchone()
        if not existing:
            return "error"

        existing_tuple = (
            norm_text(existing[0]),
            norm_text(existing[1]),
            existing[2],   # effective je datetime že OK
            existing[3],   # expires enako
            norm_text(existing[4]),
            norm_text(existing[5])
        )

        new_tuple = (
            norm_text(event.get("description")),
            norm_text(event.get("instruction")),
            norm_datetime(event.get("effective")),
            norm_datetime(event.get("expires")),
            norm_text(event.get("severity")),
            norm_text(event.get("urgency"))
        )

        if existing_tuple == new_tuple:
            return "duplicate_no_change"

        # UPDATE
        cursor.execute("""
            UPDATE organization_events
            SET description = %s,
                instruction = %s,
                effective = %s,
                expires = %s,
                severity = %s,
                urgency = %s,
                created_at = CURRENT_TIMESTAMP
            WHERE organization_id = %s
            AND type = %s
            AND area = %s
            AND headline = %s;
        """, (
            norm_text(event.get("description")),
            norm_text(event.get("instruction")),
            norm_datetime(event.get("effective")),
            norm_datetime(event.get("expires")),
            norm_text(event.get("severity")),
            norm_text(event.get("urgency")),
            event["organization_id"],
            event["type"],
            event["area"],
            event["headline"]
        ))

        conn.commit()
        return "updated"

    except Exception as e:
        conn.rollback()
        print("DB error:", e)
        return "error"

    finally:
        cursor.close()
        conn.close()

def get_organization_id_by_name(org_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    clean_name = " ".join(org_name.split())

    try:
        cursor.execute("""
            SELECT organization_id FROM organizations WHERE organization_name = %s
        """, (clean_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error finding ID for '{clean_name}': {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_events(organization_id=None, area=None, effective=None, expires=None, urgency=None):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        query = "SELECT * FROM organization_events WHERE TRUE"
        params = []

        if organization_id is not None:
            query += " AND organization_id = %s"
            params.append(organization_id)
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

def get_all_organizations():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT organization_id, organization_name FROM organizations ORDER BY organization_id;")
        return cursor.fetchall()
    except Exception as e:
        print(f"Error fetching organizations: {e}")
        return []
    finally:
        cursor.close()
        conn.close()
