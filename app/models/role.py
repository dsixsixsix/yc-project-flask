"""Модель роли."""
from app import db


class Role(db.Model):
    """Роль пользователя."""

    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))

    def to_dict(self):
        """Преобразование в словарь."""
        return {"id": self.id, "name": self.name, "description": self.description}
