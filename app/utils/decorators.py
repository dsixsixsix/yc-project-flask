"""Декораторы для проверки прав доступа."""
from functools import wraps

from flask import jsonify

from app.services.auth import get_current_user


def require_role(*allowed_roles):
    """Декоратор для проверки роли пользователя."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Authentication required"}), 401
            if user.role.name not in allowed_roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)

        return decorated_function

    return decorator
