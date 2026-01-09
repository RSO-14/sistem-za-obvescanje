import os
import logging
import requests
from html import escape

logging.basicConfig(level=logging.INFO, force=True)

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
NOTIFICATION_FUNCTION_TOKEN = os.getenv("NOTIFICATION_FUNCTION_TOKEN")
BREVO_URL = "https://api.brevo.com/v3/smtp/email"

def _format_value(value):
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value

def build_event_body(event: dict) -> str:
    lines = []
    lines.append("You have received a new system alert.\n")

    def add(label, key):
        value = _format_value(event.get(key))
        if value:
            safe = escape(str(value))
            lines.append(f"<strong>{escape(label)}:</strong> {safe}<br>")

    add("Event name", "headline")
    add("Type", "type")
    add("Area", "area")
    add("Description", "description")
    add("Instructions", "instruction")
    add("Valid from", "effective")
    add("Valid until", "expires")
    add("Severity", "severity")
    add("Urgency", "urgency")

    lines.append("\n—\nAlertHub")
    return "".join(lines)

def send_emails(payload: dict):
    if not BREVO_API_KEY or not SENDER_EMAIL:
        logging.error("[SERVERLESS] Missing BREVO_API_KEY or SENDER_EMAIL env var")
        raise RuntimeError("Missing BREVO_API_KEY or SENDER_EMAIL env var")

    event = payload.get("event")
    recipients = payload.get("recipients", [])

    to_list = []
    for r in recipients:
        if isinstance(r, dict):
            email = r.get("email")
        else:
            email = r
        if isinstance(email, str) and email.strip():
            to_list.append({"email": email.strip()})

    if not event:
        logging.warning("[SERVERLESS] Missing event in payload")
        return

    if not to_list:
        logging.info("[SERVERLESS] No valid recipients")
        return

    subject = f"Alert: {event.get('headline', 'Event')}"
    body = build_event_body(event)

    payload_json = {
        "sender": {"email": SENDER_EMAIL, "name": "AlertHub"},
        "to": to_list,
        "subject": subject,
        "htmlContent": body
    }

    try:
        resp = requests.post(
            BREVO_URL,
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload_json,
            timeout=10
        )
        
        if resp.status_code >= 400:
            logging.error(f"[SERVERLESS ERROR] status={resp.status_code} body={resp.text}")
            resp.raise_for_status()

        msg_id = None
        try:
            msg_id = resp.json().get("messageId")
        except Exception:
            pass

        logging.info(f"[SERVERLESS] Email sent to {len(to_list)} recipients"
                     + (f" | messageId={msg_id}" if msg_id else ""))
        
        # TODO: add when serverless function is ready
        # return {"sent": len(to_list), "messageId": msg_id}

    except requests.HTTPError:
        logging.error(f"[SERVERLESS ERROR] status={resp.status_code} body={resp.text}")
        raise
    except Exception as e:
        logging.error(f"[SERVERLESS EXCEPTION] {e}")
        raise
    
def notify(request):
    if NOTIFICATION_FUNCTION_TOKEN:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {NOTIFICATION_FUNCTION_TOKEN}":
            return ("Unauthorized", 401)

    try:
        payload = request.get_json(silent=True)
        if not payload:
            return ("Missing JSON body", 400)

        result = send_emails(payload)
        return (result, 200)

    except Exception as e:
        logging.exception(f"[FUNCTION EXCEPTION] {e}")
        return ("Internal Server Error", 500)