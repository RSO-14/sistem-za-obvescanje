from typing import Optional, List
from datetime import datetime
import strawberry

@strawberry.type
class User:
    id: str
    username: str
    email: str
    address: str
    region: List[str]
    alerts: List[List[str]]
    phone_number: str
    role: str
    created_at: str

@strawberry.input
class UserInput:
    username: str
    email: str
    password: str
    address: Optional[str] = None
    region: Optional[List[str]] = None
    alerts: Optional[List[List[str]]] = None
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