from typing import Optional, List
from datetime import datetime
import strawberry

@strawberry.type
class User:
    id: str
    username: Optional[str] = None
    email: str
    address: Optional[str] = None
    region: Optional[List[str]] = None
    alerts: Optional[List[List[str]]] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    created_at: Optional[str] = None

@strawberry.input
class UserInput:
    username: Optional[str]
    email: str
    password: str
    address: Optional[str] = None
    region: Optional[List[str]] = None
    alerts: Optional[List[List[str]]] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None

@strawberry.input
class LoginInput:
    email: str
    password: str

@strawberry.type
class AuthResponse:
    token: str
    user: User