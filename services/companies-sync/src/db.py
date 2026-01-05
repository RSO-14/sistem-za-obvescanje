# companies-sync/db.py

from datetime import datetime
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import os
from dateutil import parser
import json
import uuid_utils as uuid

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
                organization_id UUID PRIMARY KEY,
                organization_name TEXT UNIQUE NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
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
    org_uuid = str(uuid.uuid7())
    try:
        cursor.execute("""
            INSERT INTO organizations (organization_id, organization_name)
            VALUES (%s, %s)
            ON CONFLICT (organization_name) DO NOTHING;
        """, (org_uuid, clean_name,))

        events_table_name = str(org_uuid) + "_organization_events"
        oncall_table_name = str(org_uuid) + "_organization_oncall"

        cursor.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                id SERIAL PRIMARY KEY,
                type TEXT NOT NULL,
                area TEXT NOT NULL,
                headline TEXT NOT NULL,
                description TEXT,
                instruction TEXT,
                effective TIMESTAMPTZ NOT NULL,
                expires TIMESTAMPTZ NOT NULL,
                severity TEXT,
                urgency TEXT,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (type, area, headline)
            );
        """).format(sql.Identifier(events_table_name)))

        cursor.execute(sql.SQL("""
            CREATE TABLE IF NOT EXISTS {} (
                id SERIAL PRIMARY KEY,
                on_call_email TEXT NOT NULL,
                on_call_from TIMESTAMPTZ NOT NULL,
                on_call_to   TIMESTAMPTZ NOT NULL,
                levels JSONB NOT NULL,
                areas  JSONB NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
        """).format(sql.Identifier(oncall_table_name)))

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error inserting organization: {e}")
    finally:
        cursor.close()
        conn.close()


def insert_oncall_schedule(org_id: int, schedule: list):
    conn = get_connection()
    cursor = conn.cursor()

    results = []
    try:
        for entry in schedule:
            levels_json = json.dumps(entry["levels"])
            areas_json = json.dumps(entry["areas"])
            start = parser.parse(entry["on_call_from"])
            end = parser.parse(entry["on_call_to"])
            email = entry["on_call_email"]

            oncall_table_name = str(org_id) + "_organization_oncall"
            cursor.execute(sql.SQL("""
                SELECT id FROM {}
                  WHERE on_call_email = %s
                  AND on_call_from = %s
                  AND on_call_to = %s
                  AND levels::text = %s
                  AND areas::text = %s;
            """).format(sql.Identifier(oncall_table_name)), (email, start, end, levels_json, areas_json))

            existing = cursor.fetchone()

            if existing:
                results.append({
                    "email": email,
                    "status": "exists"
                })
                continue

            oncall_table_name = str(org_id) + "_organization_oncall"
            cursor.execute(sql.SQL("""
                INSERT INTO {} (
                    on_call_email, on_call_from, on_call_to,
                    levels, areas
                )
                VALUES (%s, %s, %s, %s, %s);
            """).format(sql.Identifier(oncall_table_name)), (
                entry["on_call_email"],
                start,
                end,
                levels_json,
                areas_json
            ))

            results.append({
                "email": entry["on_call_email"],
                "status": "inserted"
            })

        conn.commit()
        return results

    except Exception as e:
        conn.rollback()
        print(f"Error inserting on-call schedule: {e}")
        return [{"status": "error", "message": str(e)}]

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
        event_table_name = str(event["organization_id"]) + "_organization_events"
        cursor.execute(sql.SQL("""
                       INSERT INTO {} (type, area, headline, description,
                                                        instruction, effective, expires, severity, urgency)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (type, area, headline)
            DO
                       UPDATE SET
                           description = EXCLUDED.description,
                           instruction = EXCLUDED.instruction,
                           effective = EXCLUDED.effective,
                           expires = EXCLUDED.expires,
                           severity = EXCLUDED.severity,
                           urgency = EXCLUDED.urgency,
                           created_at = CURRENT_TIMESTAMP
                           RETURNING id;
                       """).format(sql.Identifier(event_table_name)), (
                           event["type"],
                           event["area"],
                           event["headline"],
                           norm_text(event.get("description")),
                           norm_text(event.get("instruction")),
                           norm_datetime(event.get("effective")),
                           norm_datetime(event.get("expires")),
                           norm_text(event.get("severity")),
                           norm_text(event.get("urgency"))
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

    if not organization_id:
        return []

    try:
        event_table_name = str(organization_id) + "_organization_events"
        query = "SELECT * FROM {} WHERE TRUE"
        params = []

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

        cursor.execute(sql.SQL(query).format(sql.Identifier(event_table_name)), params)
        return cursor.fetchall()
    except Exception as e:
        print(f"Error retrieving events: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def get_active_events(organization_id: int, areas: list):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    if not organization_id or not areas or len(areas) == 0:
        return []

    try:
        event_table_name = str(organization_id) + "_organization_events"
        if len(areas) == 1:
            query = """
                SELECT *
                FROM {}
                WHERE organization_id = %s
                  AND area = %s
                  AND expires >= NOW()
            """
            params = [organization_id, areas[0]]

        else:
            placeholders = ",".join(["%s"] * len(areas))
            query = f"""
                SELECT *
                FROM {{}}
                WHERE organization_id = %s
                  AND area IN ({placeholders})
                  AND expires >= NOW()
            """
            params = [organization_id] + areas

        cursor.execute(sql.SQL(query).format(sql.Identifier(event_table_name)), params)
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

def get_active_oncall(org_id: int, area: str):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        oncall_table_name = str(org_id) + "_organization_oncall"
        cursor.execute(sql.SQL("""
            SELECT 
                on_call_email AS email,
                levels,
                areas
            FROM {}
              WHERE NOW() BETWEEN on_call_from AND on_call_to;
        """).format(sql.Identifier(oncall_table_name)))

        rows = cursor.fetchall()
        filtered = [
            {
                "email": row["email"],
                "levels": row["levels"]
            }
            for row in rows
            if area in row["areas"]
        ]

        return filtered

    except Exception as e:
        print("Error fetching active on-call:", e)
        return []
    finally:
        cursor.close()
        conn.close()

# TODO - delete
def get_all_oncall():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    try:
        cursor.execute("""
            SELECT
                id,
                organization_id,
                on_call_email AS email,
                on_call_from,
                on_call_to,
                levels,
                areas,
                created_at
            FROM organization_oncall
            ORDER BY organization_id, on_call_from;
        """)
        return cursor.fetchall()

    except Exception as e:
        print("Error fetching on-call schedule:", e)
        return []
    finally:
        cursor.close()
        conn.close()