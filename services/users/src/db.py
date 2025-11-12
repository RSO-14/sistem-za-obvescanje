from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

uri = "mongodb+srv://zn1755:oPdqbkgiGwDq3dt5@cluster0.7oddtcy.mongodb.net/?appName=Cluster0"

client = MongoClient(uri, server_api=ServerApi('1'))
db = client.user_service

users_collection = db.users

# Test connection
try:
    client.admin.command('ping')
    print("Connected to MongoDB!")
except Exception as e:
    print(f"Error: {e}")