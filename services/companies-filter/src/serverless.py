import os
import logging
import requests

logging.basicConfig(level=logging.INFO, force=True)

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_NAME = os.getenv("SENDER_NAME", "AlertHub")

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
            lines.append(f"<strong>{label}:</strong> {value}<br>")

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
    event = payload.get("event")
    recipients = payload.get("recipients", [])

    if not event:
        logging.warning("[SERVERLESS] Missing event in payload")
        return

    if not recipients:
        logging.info("[SERVERLESS] No recipients to notify")
        return

    subject = f"Alert: {event.get('headline', 'Event')}"
    body = build_event_body(event)

    to_list = [
        {"email": r["email"]}
        for r in recipients
        if r.get("email")
    ]

    if not to_list:
        logging.info("[SERVERLESS] No valid email addresses")
        return

    payload_json = {
        "sender": {
            "email": SENDER_EMAIL,
            "name": SENDER_NAME
        },
        "to": to_list,
        "subject": subject,
        "htmlContent": body.replace("\n", "<br>")
    }

    try:
        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": BREVO_API_KEY,
                "Content-Type": "application/json"
            },
            json=payload_json,
            timeout=10
        )

        if response.status_code in (200, 201):
            logging.info(
                f"[SERVERLESS] Email sent to {len(to_list)} recipients | response={response.json()}"
            )
        else:
            logging.error(
                f"[SERVERLESS ERROR] status={response.status_code} body={response.text}"
            )

    except Exception as e:
        logging.error(f"[SERVERLESS EXCEPTION] {e}")