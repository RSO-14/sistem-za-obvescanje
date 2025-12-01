from fastapi import FastAPI
from typing import Optional
from db import get_events, insert_organization, get_organization_id_by_name
from datetime import datetime

app = FastAPI()

@app.get("/health")
def health():
    return{"status": "ok"}
    
@app.get("/events")
def api_get_events(
    organization_id: str,
    area: Optional[str] = None,
    effective: Optional[datetime] = None,
    expires: Optional[datetime] = None,
    urgency: Optional[str] = None
):
    return get_events(organization_id, area, effective, expires, urgency)

@app.post("/organizations")
def api_create_organization(name: str):
    insert_organization(name)
    org_id=get_organization_id_by_name(name)
    
    if org_id is None:
        return {"error": "Failed to insert or retrieve organization"}
    return {"organization_id": org_id, "organization_name": name}