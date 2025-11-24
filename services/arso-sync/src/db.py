import psycopg2
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


def create_tables():
    """Create necessary tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        print("Creating tables...")
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS alert_info
                       (
                           id SERIAL PRIMARY KEY,
                           alert_identifier TEXT,
                           language TEXT,
                           event TEXT,
                           effective TIMESTAMPTZ,
                           onset TIMESTAMPTZ,
                           expires TIMESTAMPTZ,
                           severity TEXT,
                           urgency TEXT,
                           certainty TEXT,
                           headline TEXT,
                           description TEXT,
                           instruction TEXT,
                           created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                           UNIQUE (alert_identifier, language, event, onset)
                           );
                       """)

        cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_alert_info_alert_identifier ON alert_info(alert_identifier);
                        CREATE INDEX IF NOT EXISTS idx_alert_info_expires ON alert_info(expires);
                        CREATE INDEX IF NOT EXISTS idx_alert_info_event ON alert_info(event);
                        CREATE INDEX IF NOT EXISTS idx_alert_info_language ON alert_info(language);
                        CREATE INDEX IF NOT EXISTS idx_alert_info_created ON alert_info(created_at);
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


def insert_alert_data(location: str, alert_data: dict):
    """Insert alert data into the database."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Insert or update the main alert
        cursor.execute("""
                       INSERT INTO alerts (identifier, sender, sent, status, location)
                       VALUES (%s, %s, %s, %s, %s) ON CONFLICT (identifier) 
            DO
                       UPDATE SET
                           sender = EXCLUDED.sender,
                           sent = EXCLUDED.sent,
                           status = EXCLUDED.status,
                           location = EXCLUDED.location
                           RETURNING identifier;
                       """, (
                           alert_data['identifier'],
                           alert_data['sender'],
                           alert_data['sent'],
                           alert_data['status'],
                           location
                       ))

        alert_identifier = cursor.fetchone()[0]

        # Insert alert info for each language and event
        for language, events in alert_data.items():
            if language in ['identifier', 'sender', 'sent', 'status']:
                continue

            for event, warnings in events.items():
                for warning in warnings:
                    cursor.execute("""
                                   INSERT INTO alert_info (alert_identifier, language, event, effective, onset,
                                                           expires, severity, urgency, certainty, headline,
                                                           description, instruction)
                                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (alert_identifier, language, event, effective)
                        DO
                                   UPDATE SET
                                       onset = EXCLUDED.onset,
                                       expires = EXCLUDED.expires,
                                       severity = EXCLUDED.severity,
                                       urgency = EXCLUDED.urgency,
                                       certainty = EXCLUDED.certainty,
                                       headline = EXCLUDED.headline,
                                       description = EXCLUDED.description,
                                       instruction = EXCLUDED.instruction;
                                   """, (
                                       alert_identifier,
                                       language,
                                       event,
                                       warning['effective'],
                                       warning['onset'],
                                       warning['expires'],
                                       warning['severity'],
                                       warning['urgency'],
                                       warning['certainty'],
                                       warning['headline'],
                                       warning['description'],
                                       warning['instruction']
                                   ))

        conn.commit()
        print(f"Data for {location} inserted successfully")
    except Exception as e:
        conn.rollback()
        print(f"Error inserting data for {location}: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
