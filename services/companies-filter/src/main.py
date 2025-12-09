import json
import os
import requests
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from datetime import datetime
from consumer import start_consumer
from graphql_client import get_user
from notifications import process_event
import logging
logging.basicConfig(level=logging.INFO, force=True)

app = FastAPI()
COMPANIES_SYNC_URL = os.getenv("COMPANIES_SYNC_URL")
subscribers = {}   # user_id → list of pending events

@app.get("/health")
def health_check():
    return {"status": "ok"}

# Call when user opens app for relavant events
@app.get("/events/{user_id}")
def get_events_for_user(user_id: str):
    user = get_user(user_id)
    user_regions = user.get("region", [])
    organization = user.get("role")

    resp = requests.get(
        f"{COMPANIES_SYNC_URL}/events/active",
        params={
            "organization_name": organization,
            "areas": ",".join(user_regions),
            "now": datetime.utcnow().isoformat()
        }
    )

    if resp.status_code != 200:
        return []
    return resp.json()

# Call when user opens app for realtime events from RabbitMQ
@app.get("/ws/events/{user_id}")
async def event_stream(user_id: str):
    async def event_generator():
        queue = subscribers.setdefault(user_id, [])

        while True:
            if queue:
                event = queue.pop(0)
                yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# RabbitMQ calls for each new event
def handle_incoming_event(event: dict):
    
    # 1. Push notifications
    logging.info("Calling process_event")
    process_event(event)
    logging.info("Ended process_event")
    # 2. Realtime app update
    logging.info("Calling broadcast_to_subscribers")
    broadcast_to_subscribers(event)
    logging.info("Ended broadcast_to_subscribers")

def broadcast_to_subscribers(event: dict):
    event_area = event.get("area")
    event_org = event.get("organization_name")

    for user_id, queue in subscribers.items():
        try:
            user = get_user(user_id)

            user_regions = user.get("region", [])
            user_org = user.get("role")

            if user_org != event_org:
                continue
            if event_area not in user_regions:
                continue
            queue.append(event)

        except Exception as e:
            print("Error broadcasting event:", e)

@app.on_event("startup")
def startup_event():
    print("Starting RabbitMQ consumer...")
    start_consumer(handle_incoming_event)