import logging
import requests
from datetime import datetime, timezone
import os
logging.basicConfig(level=logging.INFO, force=True)

USERS_SERVICE_URL = os.getenv("USERS_SERVICE_URL")
COMPANIES_SYNC_URL = os.getenv("COMPANIES_SYNC_URL")

def graphql(query: str, variables: dict = None):
    resp = requests.post(
        USERS_SERVICE_URL,
        json={"query": query, "variables": variables or {}}
    )

    try:
        return resp.json().get("data")
    except:
        logging.error("GraphQL error:", resp.text)
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

    logging.info(f"[NOTIF] Processing event='{headline}', org='{org}', area='{area}', level='{level}'")
    notified = set()

    # 1) On-call
    oncall_emails = get_oncall_notifications(event)
    for user in oncall_emails:
        logging.info(f"[NOTIFICATION - ONCALL] → {user} | {headline}")
        notified.add(user["email"])

    # 2) Regular users
    regular_emails = get_regular_user_notifications(event)
    for user in regular_emails:
        if user["email"] not in notified:
            logging.info(f"[NOTIFICATION - USER] → {user} | {headline}")
            notified.add(user["email"])

    if not notified:
        logging.info("[NOTIFICATION] No one to notify.")

    return list(notified)