"""Маршруты для аутентификации."""
import os

from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash

from flask import current_app

from app import db
from app.models.role import Role
from app.models.user import User
from app.services.auth import generate_token

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=["POST"])
def register():
    """Регистрация нового пользователя."""
    data = request.json
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "username and password required"}), 400

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 400

    role = Role.query.filter_by(name="user").first()
    if not role:
        return jsonify({"error": "Default role not found"}), 500

    user = User(
        username=data["username"],
        password_hash=generate_password_hash(data["password"]),
        role_id=role.id,
    )
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    token = generate_token(user.id, user.username, user.role.name)
    current_app.logger.info("User registered: %s with role: %s", user.username, user.role.name)
    return jsonify({"token": token, "user": user.to_dict()}), 201


@bp.route("/login", methods=["POST"])
def login():
    """Аутентификация пользователя и получение токена."""
    data = request.json
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "username and password required"}), 400

    user = User.query.filter_by(username=data["username"]).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_token(user.id, user.username, user.role.name)
    current_app.logger.info("User logged in: %s with role: %s", user.username, user.role.name)
    return jsonify({"token": token, "user": user.to_dict()})
