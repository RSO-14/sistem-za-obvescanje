import os
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from consumer import start_consumer
from graphql_client import get_user
from notifications import handle_event
import logging
logging.basicConfig(level=logging.INFO, force=True)

app = FastAPI()
origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # use ["*"] to allow any origin (not recommended in production)
    allow_credentials=True,
    allow_methods=["*"],          # or restrict: ["GET", "POST", "OPTIONS"]
    allow_headers=["*"],          # or restrict to specific headers

)
COMPANIES_SYNC_URL = os.getenv("COMPANIES_SYNC_URL")
ARSO_SYNC_URL = os.getenv("ARSO_SYNC_URL")
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

    if organization == 'public':
        base_request_url = ARSO_SYNC_URL
    else:
        base_request_url = COMPANIES_SYNC_URL

    resp = requests.get(
        f"{base_request_url}/events/active",
        params={
            "organization_name": organization,
            "areas": ",".join(user_regions)
        }
    )

    if resp.status_code != 200:
        return []
    return resp.json()


# RabbitMQ calls for each new event
def handle_incoming_event(event: dict, routing_key: str):
     logging.info("Calling process_event")
     handle_event(event, routing_key)
     logging.info("Ended process_event")

@app.on_event("startup")
def startup_event():
     print("Starting RabbitMQ consumer...")
     start_consumer(handle_incoming_event)