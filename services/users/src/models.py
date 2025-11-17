from typing import Optional
from datetime import datetime
import strawberry

@strawberry.type
class User:
    id: str
    username: str
    email: str
    address: str
    region: str
    phone_number: str
    role: str
    created_at: str

@strawberry.input
class UserInput:
    username: str
    email: str
    password: str
    address: Optional[str] = None
    region: str
    phone_number: Optional[str] = None
    role: str


@strawberry.input
class LoginInput:
    username: str
    password: str

@strawberry.type
class AuthResponse:
    token: str
    user: User