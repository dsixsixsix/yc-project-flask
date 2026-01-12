"""Модель элемента."""
from datetime import datetime

from app import db
from app.models.user import User


class Item(db.Model):
    """Элемент для CRUD операций."""

    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(512), nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship("User", backref="items")

    def to_dict(self):
        """Преобразование в словарь."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "file_url": self.file_url,
            "created_by": self.created_by,
        }
