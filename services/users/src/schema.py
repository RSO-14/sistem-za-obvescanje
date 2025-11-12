import strawberry
from typing import Optional
from .models import User, UserInput, LoginInput, AuthResponse
from .db import users_collection
from .auth import hash_password, verify_password, create_token
from datetime import datetime


@strawberry.type
class Query:
    @strawberry.field
    def user(self, id: str) -> Optional[User]:
        user_data = users_collection.find_one({"_id": id})
        if user_data:
            return User(
                id=str(user_data["_id"]),
                username=user_data["username"],
                email=user_data["email"],
                created_at=user_data["created_at"]
            )
        return None


@strawberry.type
class Mutation:
    @strawberry.mutation
    def register(self, input: UserInput) -> AuthResponse:
        if users_collection.find_one({"username": input.username}):
            raise Exception("Username already exists")

        user_id = str(users_collection.count_documents({}) + 1)
        user_doc = {
            "_id": user_id,
            "username": input.username,
            "email": input.email,
            "password": hash_password(input.password),
            "created_at": datetime.utcnow().isoformat()
        }
        users_collection.insert_one(user_doc)

        token = create_token(user_id)
        user = User(
            id=user_id,
            username=input.username,
            email=input.email,
            created_at=user_doc["created_at"]
        )
        return AuthResponse(token=token, user=user)

    @strawberry.mutation
    def login(self, input: LoginInput) -> AuthResponse:
        user_data = users_collection.find_one({"username": input.username})
        if not user_data or not verify_password(input.password, user_data["password"]):
            raise Exception("Invalid credentials")

        token = create_token(str(user_data["_id"]))
        user = User(
            id=str(user_data["_id"]),
            username=user_data["username"],
            email=user_data["email"],
            created_at=user_data["created_at"]
        )
        return AuthResponse(token=token, user=user)


schema = strawberry.Schema(query=Query, mutation=Mutation)