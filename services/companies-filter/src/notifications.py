import logging
import requests
from datetime import datetime, timezone
import os
import time

logging.basicConfig(level=logging.INFO, force=True)

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")
COMPANIES_SYNC_URL = os.getenv("COMPANIES_SYNC_URL")
NOTIFICATION_FUNCTION_URL = os.getenv("NOTIFICATION_FUNCTION_URL")
NOTIFICATION_FUNCTION_TOKEN = os.getenv("NOTIFICATION_FUNCTION_TOKEN")

def trigger_notification_function(payload: dict) -> None:
    if not NOTIFICATION_FUNCTION_URL or NOTIFICATION_FUNCTION_URL == "REPLACE_ME":
        logging.warning("[NOTIF → FUNCTION] Notification function disabled (URL not set).")
        return

    headers = {"Content-Type": "application/json"}
    if NOTIFICATION_FUNCTION_TOKEN:
        headers["Authorization"] = f"Bearer {NOTIFICATION_FUNCTION_TOKEN}"

    resp = requests.post(
        NOTIFICATION_FUNCTION_URL,
        json=payload,
        headers=headers,
        timeout=10
    )

    if resp.status_code >= 400:
        logging.error(f"[NOTIF → FUNCTION] status={resp.status_code} body={resp.text}")
        resp.raise_for_status()
    logging.info("[NOTIF → FUNCTION] Triggered notification-function successfully.")
    
def handle_event(event: dict, routing_key: str):
    """
    routing_key:
      - companies → normal company logic (on-call + regular users)
      - arso      → PUBLIC users only, no on-call
    """
    if routing_key == "arso":
        event["organization_name"] = "public"
        event["_skip_oncall"] = True
    else:
        event["_skip_oncall"] = False

    payload = process_event(event)

    if not payload:
        logging.info("[HANDLE EVENT] No notifications to send")
        return

    try:
        trigger_notification_function(payload)
    except Exception as e:
        logging.error(f"[SERVERLESS ERROR] {e}")

def graphql(query: str, variables: dict = None):
    for i in range(3):
        try:
            resp = requests.post(
                USERS_SERVICE_URL,
                json={"query": query, "variables": variables or {}},
                timeout=15
            )
            return resp.json().get("data")
        except Exception as e:
            logging.error(f"[GRAPHQL ERROR] attempt {i+1}/3): {e}")
            time.sleep(1)
    return None
    
def get_oncall_notifications(event):
    org = event["organization_name"]
    area = event["area"]
    now = datetime.now(timezone.utc).isoformat()

    logging.info(f"[ONCALL] Requesting on-call: org={org}, area={area}, now={now}")

    try:
        # Get on-call entries
        resp = requests.get(
            f"{COMPANIES_SYNC_URL}/oncall/active",
            params={"organization_name": org, "area": area, "now": now},
            timeout=5
        )
        logging.info(f"[ONCALL] Raw: {resp.text}")

        if resp.status_code != 200:
            return []

        data = resp.json()
        level = event.get("severity")

        # Filter by severity
        filtered = [
            oc for oc in data
            if level in oc.get("levels", [])
        ]
        logging.info(f"[ONCALL] Matched oncall entries: {filtered}")

        # Call users → userByEmail for each matched oncall email
        results = []
        for oc in filtered:
            email = oc["email"]

            gql_query = """
            query($email: String!) {
              userByEmail(email: $email) {
                email
                phoneNumber
              }
            }
            """

            gql_vars = {"email": email}
            user_data = graphql(gql_query, gql_vars)
            logging.info(f"[ONCALL] userByEmail({email}) → {user_data}")

            if user_data and user_data.get("userByEmail"):
                ud = user_data["userByEmail"]
                results.append({
                    "email": ud.get("email"),
                    "phone": ud.get("phoneNumber")
                })
            else:
                logging.warning(f"[ONCALL] No user detail found for {email}")

        logging.info(f"[ONCALL] Final oncall notifications: {results}")
        return results

    except Exception as e:
        logging.error(f"[ONCALL ERROR] {e}")
        return []


def get_regular_user_notifications(event):
    org = event["organization_name"]
    area = event["area"]
    level = event["severity"]

    query = """
    query($company: String!, $region: String!, $level: String!) {
      usersByCompanyAlert(company: $company, region: $region, level: $level) {
        email
        phoneNumber
      }
    }
    """
    variables = {
        "company": org,
        "region": area,
        "level": level
    }

    result = graphql(query, variables)
    logging.info(f"[USERS] Raw GraphQL result: {result}")

    if not result or "usersByCompanyAlert" not in result:
        logging.info("[USERS] No users found")
        return []

    users = result["usersByCompanyAlert"]
    final = []
    for u in users:
        final.append({
            "email": u.get("email"),
            "phone": u.get("phoneNumber")
        })

    logging.info(f"[USERS] Final regular user notifications: {final}")
    return final
    
def process_event(event: dict):
    headline = event.get("headline")
    org = event.get("organization_name")
    area = event.get("area")
    level = event.get("severity")

    logging.info(
        f"[NOTIF] Processing event='{headline}', org='{org}', area='{area}', level='{level}'"
    )

    if not org or not area:
        logging.warning("[NOTIF] Missing organization_name or area")
        return None

    recipients = []
    seen = set()

    # 1) ON-CALL (only for companies)
    if not event.get("_skip_oncall", False):
        for u in get_oncall_notifications(event):
            email = u.get("email")
            if email and email not in seen:
                seen.add(email)
                recipients.append({
                    "email": email,
                    "group": "oncall"
                })

    # 2) Regular users
    for u in get_regular_user_notifications(event):
        email = u.get("email")
        if email and email not in seen:
            seen.add(email)
            recipients.append({
                "email": email,
                "group": "regular"
            })

    if not recipients:
        logging.info("[NOTIF] No recipients for this event.")
        return None

    payload = {
        "event": event,
        "recipients": recipients
    }

    logging.info("[NOTIF → SERVERLESS] Payload prepared:")
    logging.info(payload)

    return payload