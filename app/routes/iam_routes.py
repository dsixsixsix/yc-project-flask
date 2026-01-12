"""Маршруты для IAM сервиса."""
import os

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from flask import current_app

from app import db
from app.models.role import Role
from app.models.user import User
from app.services.auth import get_current_user, get_user_permissions, verify_token

bp = Blueprint("iam", __name__, url_prefix="/iam")


@bp.route("/verify", methods=["POST"])
def iam_verify():
    """
    IAM сервис: проверка токена и возврат информации о пользователе и его правах.
    Эквивалент Yandex Cloud IAM.
    """
    data = request.json
    if not data or not data.get("token"):
        return jsonify({"error": "token required"}), 400

    payload = verify_token(data["token"])
    if not payload:
        return jsonify({"error": "Invalid or expired token"}), 401

    user = User.query.get(payload["user_id"])
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify(
        {
            "valid": True,
            "user": user.to_dict(),
            "role": user.role.name,
            "permissions": get_user_permissions(user),
        }
    )


@bp.route("/user", methods=["GET"])
def iam_get_current_user():
    """IAM сервис: получение информации о текущем пользователе по токену."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    return jsonify(
        {
            "user": user.to_dict(),
            "role": user.role.name,
            "permissions": get_user_permissions(user),
        }
    )


def init_test_users():
    """Создание тестовых пользователей (admin, user, guest) для демонстрации."""
    test_users = [
        {"username": "admin", "password": "admin123", "role": "admin"},
        {"username": "user", "password": "user123", "role": "user"},
        {"username": "guest", "password": "guest123", "role": "guest"},
    ]

    created = []
    for user_data in test_users:
        existing = User.query.filter_by(username=user_data["username"]).first()
        if existing:
            continue

        role = Role.query.filter_by(name=user_data["role"]).first()
        if not role:
            continue

        user = User(
            username=user_data["username"],
            role_id=role.id,
        )
        user.set_password(user_data["password"])
        db.session.add(user)
        created.append(user_data["username"])

    db.session.commit()
    current_app.logger.info(
        "Created test users: %s",
        ", ".join(created) if created else "none (already exist)",
    )
    return jsonify({"message": "Test users initialized", "created": created})
