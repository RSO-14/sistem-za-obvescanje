from typing import Optional
from datetime import datetime
import strawberry

@strawberry.type
class User:
    id: str
    username: str
    email: str
    created_at: str

@strawberry.input
class UserInput:
    username: str
    email: str
    password: str

@strawberry.input
class LoginInput:
    username: str
    password: str

@strawberry.type
class AuthResponse:
    token: str
    user: User