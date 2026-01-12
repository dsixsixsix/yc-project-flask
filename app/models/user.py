"""Модель пользователя."""
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models.role import Role


class User(db.Model):
    """Пользователь системы."""

    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    role = db.relationship("Role", backref="users")

    def to_dict(self):
        """Преобразование в словарь."""
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role.name if self.role else None,
        }

    def check_password(self, password):
        """Проверка пароля."""
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        """Установка пароля."""
        self.password_hash = generate_password_hash(password)
