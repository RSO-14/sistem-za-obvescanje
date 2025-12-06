from fastapi import FastAPI, HTTPException
from typing import Optional
from datetime import datetime
from publisher import publish_event
from db import (
    get_events,
    insert_organization,
    get_organization_id_by_name,
    insert_or_update_event,
    create_tables,
    get_all_organizations,
    insert_oncall_schedule,
    get_active_oncall,
    get_active_events,
    get_all_oncall
)

app = FastAPI()
create_tables()

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

    if not org_name:
        raise HTTPException(status_code=400, detail="Missing organization_name")

    insert_organization(org_name)
    org_id = get_organization_id_by_name(org_name)
    results = []

    for event in events:
        event["organization_id"] = org_id
        event["organization_name"] = org_name
        status = insert_or_update_event(event)

        if status in ("inserted", "updated"):
            publish_event(event)

        results.append({
            "headline": event["headline"],
            "status": status
        })

    return {
        "organization": org_name,
        "results": results
    }
    
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
def api_get_oncall(organization_name: str, area: str, now: datetime):
    org_id = get_organization_id_by_name(organization_name)
    if not org_id:
        raise HTTPException(status_code=404, detail="Organization not found")

    return get_active_oncall(org_id, now, area)

@app.get("/events/active")
def api_get_active_events(organization_name: str,areas: str, now: datetime):
    org_id = get_organization_id_by_name(organization_name)
    if not org_id:
        raise HTTPException(status_code=404, detail="Organization not found")

    areas_list = [a.strip() for a in areas.split(",") if a.strip()]
    return get_active_events(org_id, areas_list, now)

@app.get("/oncall")
def api_get_all_oncall():
    return get_all_oncall()