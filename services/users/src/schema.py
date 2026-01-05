import strawberry
from typing import Optional, List
from .auth import get_current_user_id
from .models import User, UserInput, LoginInput, AuthResponse
from .db import users_collection
from .auth import hash_password, verify_password, create_token
from datetime import datetime


@strawberry.type
class Query:
    @strawberry.field
    def me(self, info) -> Optional[User]:
        user_id = get_current_user_id(info)
        if not user_id:
            return None
        user_data = users_collection.find_one({"_id": user_id})
        if not user_data:
            return None
        return User(
            id=str(user_data["_id"]),
            email=user_data["email"],
            address=user_data.get("address", ""),
            region=user_data.get("region") or [],
            phone_number=user_data.get("phone_number", ""),
            role=user_data.get("role", ""),
            created_at=user_data.get("created_at", datetime.utcnow().isoformat()),
        )

    @strawberry.field
    def user(self, id: str) -> Optional[User]:
        user_data = users_collection.find_one({"_id": id})
        if user_data:
            return User(
                id=str(user_data["_id"]),
                email=user_data["email"],
                address=user_data.get("address") or "",
                region=user_data.get("region") or [],
                alerts=user_data.get("alerts") or [],
                phone_number=user_data.get("phone_number") or "",
                role=user_data["role"],
                created_at=user_data["created_at"]
            )
        return None

    @strawberry.field
    def user_by_email(self, email: str) -> Optional[User]:
        user = users_collection.find_one({"email": email})
        if not user:
            return None

        return User(
            id=str(user["_id"]),
            email=user["email"],
            address=user.get("address") or "",
            region=user.get("region") or [],
            alerts=user.get("alerts") or [],
            phone_number=user.get("phone_number") or "",
            role=user.get("role") or "",
            created_at=user.get("created_at")
        )

    @strawberry.field
    def users_by_region(self, region: str) -> list[User]:
        users_data = users_collection.find({"region": {"$in": [region]}})
        return [
            User(
                id=str(user["_id"]),
                email=user["email"],
                address=user.get("address") or "",
                region=user.get("region") or [],
                alerts=user.get("alerts") or [],
                phone_number=user.get("phone_number") or "",
                role=user["role"],
                created_at=user["created_at"]
            )
            for user in users_data
        ]

    @strawberry.field
    def users_by_alert(self, region: str, level: str) -> List[User]:
        users_cursor = users_collection.find({
            "alerts": {"$exists": True, "$ne": None}
        })

        matched_users = []
        for user in users_cursor:
            alerts = user.get("alerts") or []  # List[List[str]]

            for alert_list in alerts:
                if region in alert_list and level in alert_list:
                    matched_users.append(user)
                    break

        return [
            User(
                id=str(user["_id"]),
                email=user["email"],
                address=user.get("address") or "",
                region=user.get("region") or [],
                alerts=user.get("alerts") or [],
                phone_number=user.get("phone_number") or "",
                role=user["role"],
                created_at=user["created_at"],
            )
            for user in matched_users
        ]

    @strawberry.field
    def users_by_company_alert(self, company: str, region: str, level: str) -> List[User]:
        users_cursor = users_collection.find({
            "role": company,
            "alerts": {"$exists": True, "$ne": None}
        })

        matched = []
        for user in users_cursor:
            alerts = user.get("alerts") or []

            for alert_list in alerts:
                if region in alert_list and level in alert_list:
                    matched.append(user)
                    break

        return [
            User(
                id=str(u["_id"]),
                email=u["email"],
                address=u.get("address") or "",
                region=u.get("region") or [],
                alerts=u.get("alerts") or [],
                phone_number=u.get("phone_number") or "",
                role=u.get("role") or "",
                created_at=u.get("created_at")
            )
            for u in matched
        ]


    @strawberry.field
    def users_by_address(self, address: str) -> list[User]:
        users_data = users_collection.find({"address": address})
        return [
            User(
                id=str(user["_id"]),
                email=user["email"],
                address=user.get("address") or "",
                region=user.get("region") or [],
                alerts=user.get("alerts") or [],
                phone_number=user.get("phone_number") or "",
                role=user["role"],
                created_at=user["created_at"]
            )
            for user in users_data
        ]

    @strawberry.field
    def users_by_role(self, role: str) -> list[User]:
        users_data = users_collection.find({"role": role})
        return [
            User(
                id=str(user["_id"]),
                email=user["email"],
                address=user.get("address") or "",
                region=user.get("region") or [],
                alerts=user.get("alerts") or [],
                phone_number=user.get("phone_number") or "",
                role=user["role"],
                created_at=user["created_at"]
            )
            for user in users_data
        ]

@strawberry.type
class Mutation:
    @strawberry.mutation
    def register(self, input: UserInput) -> AuthResponse:
        if users_collection.find_one({"email": input.email}):
            raise Exception("Email already exists")

        user_id = str(users_collection.count_documents({}) + 1)
        user_doc = {
            "_id": user_id,
            "email": input.email,
            "password": hash_password(input.password),
            "address": input.address,
            "region": input.region or [],
            "alerts": input.alerts or [], 
            "phone_number": input.phone_number,
            "role": input.role,
            "created_at": datetime.utcnow().isoformat()
        }
        users_collection.insert_one(user_doc)

        token = create_token(user_id)
        user = User(
            id=user_id,
            email=input.email,
            address=input.address or "",
            region=input.region or [],
            alerts=input.alerts or [], 
            phone_number=input.phone_number or "",
            role=input.role,
            created_at=user_doc["created_at"]
        )
        return AuthResponse(token=token, user=user)

    @strawberry.mutation
    def login(self, input: LoginInput) -> AuthResponse:
        user_data = users_collection.find_one({"email": input.email})
        if not user_data or not verify_password(input.password, user_data["password"]):
            raise Exception("Invalid credentials")

        token = create_token(str(user_data["_id"]))
        user = User(
            id=str(user_data["_id"]),
            email=user_data["email"],
            address=user_data.get("address", ""),
            region=user_data.get("region") or [],
            phone_number=user_data.get("phone_number", ""),
            role=user_data.get("role", ""),
            created_at=user_data.get("created_at", datetime.utcnow().isoformat()),
        )
        return AuthResponse(token=token, user=user)


schema = strawberry.Schema(query=Query, mutation=Mutation)