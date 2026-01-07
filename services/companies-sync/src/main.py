# companies-sync/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime, timezone
from publisher import publish_event
import logging
import time
from db import (
    get_events,
    insert_organization,
    get_organization_id_by_name,
    insert_or_update_event,
    create_tables,
    get_all_organizations,
    insert_oncall_schedule,
    get_active_oncall,
    get_active_events
)

logging.basicConfig(level=logging.INFO)

app = FastAPI()

origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # use ["*"] to allow any origin (not recommended in production)
    allow_credentials=True,
    allow_methods=["*"],          # or restrict: ["GET", "POST", "OPTIONS"]
    allow_headers=["*"],          # or restrict to specific headers

)

@app.on_event("startup")
def startup():
    for i in range(10):
        try:
            create_tables()
            logging.info("DB ready, tables ensured.")
            return
        except Exception as e:
            logging.warning(f"DB not ready ({i+1}/10): {e}")
            time.sleep(2)
    raise RuntimeError("DB not reachable after retries")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/events")
def api_get_events(
    organization_id: Optional[int] = None,
    organization_name: Optional[str] = None,
    area: Optional[str] = None,
    effective: Optional[datetime] = None,
    expires: Optional[datetime] = None,
    urgency: Optional[str] = None
):
    if organization_id is None and organization_name:
        organization_id = get_organization_id_by_name(organization_name)
        if organization_id is None:
            raise HTTPException(status_code=404, detail="Organization not found")

    return get_events(organization_id, area, effective, expires, urgency)

@app.post("/organizations")
def api_create_organization(name: str):
    print(f"Creating organization: {name}")
    old_id = get_organization_id_by_name(name)
    insert_organization(name)
    new_id = get_organization_id_by_name(name)

    if old_id:
        return {
            "status": "exists",
            "organization_id": old_id,
            "message": "Organization already existed. No new insert."
        }
    if new_id:
        return {
            "status": "inserted",
            "organization_id": new_id,
            "message": "Organization successfully created."
        }

    return {"error": "Failed to insert or retrieve organization"}

@app.post("/events")
def api_receive_events(payload: dict):
    org_name = payload.get("organization_name")
    events = payload.get("events", [])
    now = datetime.now(timezone.utc)

    if not org_name:
        raise HTTPException(status_code=400, detail="Missing organization_name")

    insert_organization(org_name)
    org_id = get_organization_id_by_name(org_name)
    results = []

    for event in events:
        event["organization_id"] = org_id
        event["organization_name"] = org_name
        status = insert_or_update_event(event)

        expires_str = event.get("expires")
        publish = True
        try:
            expires_dt = datetime.fromisoformat(expires_str)
            expires = expires_dt.replace(tzinfo=timezone.utc)
            if expires < now:
                publish = False
        except Exception as e:
            publish = False
            
        if status in ("inserted", "updated") and publish:
            publish_event(event)

        results.append({
            "headline": event["headline"],
            "status": status,
            "publish": publish
        })

    return {
        "organization": org_name,
        "results": results
    }

# TODO - delete for safety reasons
@app.get("/organizations")
def api_get_organizations():
    return [
        {"organization_id": org_id, "organization_name": name}
        for (org_id, name) in get_all_organizations()
    ]


@app.post("/organizations/{org_name}/oncall")
def api_add_oncall(org_name: str, payload: dict):
    org_id = get_organization_id_by_name(org_name)
    if not org_id:
        raise HTTPException(status_code=404, detail="Organization not found")

    schedule = payload.get("on_call")
    if not schedule or not isinstance(schedule, list):
        raise HTTPException(status_code=400, detail="Missing or invalid on_call list")

    results = insert_oncall_schedule(org_id, schedule)
    return {
        "organization_id": org_id,
        "results": results
    }

@app.get("/oncall/active")
def api_get_oncall(organization_name: str, area: str):
    org_id = get_organization_id_by_name(organization_name)
    if not org_id:
        raise HTTPException(status_code=404, detail="Organization not found")

    return get_active_oncall(org_id, area)


@app.get("/events/active")
def api_get_active_events(organization_name: str, areas: str):
    org_id = get_organization_id_by_name(organization_name)
    if not org_id:
        raise HTTPException(status_code=404, detail="Organization not found")

    areas_list = [a.strip() for a in areas.split(",") if a.strip()]
    return get_active_events(org_id, areas_list)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)