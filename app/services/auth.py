"""Сервис аутентификации и авторизации."""
import os
from datetime import datetime, timedelta

import jwt
from flask import current_app, request

from app import db
from app.models.user import User


def generate_token(user_id, username, role):
    """Генерирует JWT токен для пользователя."""
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def verify_token(token):
    """Проверяет JWT токен и возвращает данные пользователя."""
    try:
        payload = jwt.decode(
            token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user():
    """Получает текущего пользователя из токена в заголовке Authorization."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    try:
        token = auth_header.split(" ")[1]  # Bearer <token>
        payload = verify_token(token)
        if payload:
            return User.query.get(payload["user_id"])
    except (IndexError, AttributeError):
        return None
    return None


def get_user_permissions(user: User) -> dict:
    """Возвращает права доступа пользователя."""
    role_name = user.role.name if user.role else "guest"
    return {
        "can_create": role_name in ["admin", "user"],
        "can_read": True,
        "can_update": role_name in ["admin", "user"],
        "can_delete": role_name == "admin",
    }
