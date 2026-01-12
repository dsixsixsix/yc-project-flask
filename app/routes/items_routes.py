"""Маршруты для CRUD операций с элементами."""
import os

from flask import Blueprint, current_app, jsonify, request

from app import db
from app.models.item import Item
from app.services.auth import get_current_user
from app.services.storage import delete_from_storage, extract_key_from_url, upload_to_storage
from app.utils.decorators import require_role

bp = Blueprint("items", __name__, url_prefix="/items")


@bp.route("", methods=["POST"])
@require_role("admin", "user")
def create_item():
    """Создание элемента. Требуется роль user или admin."""
    user = get_current_user()
    name = request.form.get("name")
    description = request.form.get("description")
    file_url = None

    if not name:
        return jsonify({"error": "name is required"}), 400

    if "file" in request.files:
        bucket = os.getenv("S3_BUCKET")
        if bucket:
            file_url = upload_to_storage(bucket, request.files["file"])

    item = Item(
        name=name, description=description, file_url=file_url, created_by=user.id
    )
    db.session.add(item)
    db.session.commit()
    current_app.logger.info(
        "Created item id=%s name=%s by user=%s", item.id, item.name, user.username
    )
    return jsonify(item.to_dict()), 201


@bp.route("", methods=["GET"])
def list_items():
    """Получение списка элементов. Доступно всем (guest, user, admin)."""
    items = Item.query.all()
    current_app.logger.info("Listed %d items", len(items))
    return jsonify([i.to_dict() for i in items])


@bp.route("/<int:item_id>", methods=["GET"])
def get_item(item_id: int):
    """Получение конкретного элемента. Доступно всем."""
    item = Item.query.get_or_404(item_id)
    current_app.logger.info("Fetched item id=%s", item.id)
    return jsonify(item.to_dict())


@bp.route("/<int:item_id>", methods=["PUT", "PATCH"])
@require_role("admin", "user")
def update_item(item_id: int):
    """Обновление элемента. User может обновлять только свои, admin - все."""
    user = get_current_user()
    item = Item.query.get_or_404(item_id)

    # Проверка прав: user может обновлять только свои элементы
    if user.role.name == "user" and item.created_by != user.id:
        return jsonify({"error": "You can only update your own items"}), 403

    data = request.form if request.form else request.json

    if not data:
        return jsonify({"error": "no data provided"}), 400

    if "name" in data:
        item.name = data["name"]
    if "description" in data:
        item.description = data["description"]

    if "file" in request.files:
        bucket = os.getenv("S3_BUCKET")
        if bucket:
            item.file_url = upload_to_storage(bucket, request.files["file"])

    db.session.commit()
    current_app.logger.info("Updated item id=%s by user=%s", item.id, user.username)
    return jsonify(item.to_dict())


@bp.route("/<int:item_id>", methods=["DELETE"])
@require_role("admin")
def delete_item(item_id: int):
    """Удаление элемента. Только admin."""
    user = get_current_user()
    item = Item.query.get_or_404(item_id)
    bucket = os.getenv("S3_BUCKET")

    # Удаляем файл из Object Storage перед удалением записи из БД
    if item.file_url and bucket:
        key = extract_key_from_url(item.file_url, bucket)
        if key:
            delete_from_storage(bucket, key)

    db.session.delete(item)
    db.session.commit()
    current_app.logger.info("Deleted item id=%s by admin=%s", item_id, user.username)
    return jsonify({"status": "deleted"})
