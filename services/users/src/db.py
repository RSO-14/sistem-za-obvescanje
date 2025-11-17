import os

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = os.getenv('MONGO_URI')

client = MongoClient(uri, server_api=ServerApi('1'))
db = client.user_service

users_collection = db.users

# Test connection
try:
    client.admin.command('ping')
    print("Connected to MongoDB!")
except Exception as e:
    print(f"Error: {e}")