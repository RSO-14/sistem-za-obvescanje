from fastapi import FastAPI, HTTPException
from typing import Optional
from datetime import datetime, timezone
import logging
from db import get_active_events

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/events/active")
def api_get_active_events(organization_name: str, areas: str):
    areas_list = [a.strip() for a in areas.split(",") if a.strip()]
    return get_active_events(areas_list)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)