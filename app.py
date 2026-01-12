import logging
import os
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.exceptions import HTTPException


load_dotenv()
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(__name__)

# SQLite for simplicity; change URI if desired.
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL", f"sqlite:///{os.path.join(os.path.dirname(__file__), 'app.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Item(db.Model):
    __tablename__ = "items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(512), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "file_url": self.file_url,
        }


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
    )


def extract_key_from_url(file_url: str, bucket: str) -> str | None:
    """Извлекает object key из сохранённого URL."""
    if not file_url:
        return None
    # Формат URL: http://localhost:9000/demo-bucket/uploads/uuid_filename
    # или: http://localhost:9000/demo-bucket/uploads/uuid_
    try:
        # Убираем endpoint и bucket из URL, оставляем только путь к объекту
        endpoint = os.getenv("S3_PUBLIC_ENDPOINT", os.getenv("S3_ENDPOINT_URL", ""))
        if endpoint:
            endpoint = endpoint.rstrip("/")
            if file_url.startswith(endpoint):
                # Убираем endpoint и bucket
                path = file_url[len(endpoint):].lstrip("/")
                if path.startswith(f"{bucket}/"):
                    key = path[len(f"{bucket}/"):]
                    return key
        # Fallback: пытаемся извлечь из стандартного формата
        if f"/{bucket}/" in file_url:
            key = file_url.split(f"/{bucket}/", 1)[1]
            return key
    except Exception as e:
        app.logger.warning("Failed to extract key from URL %s: %s", file_url, e)
    return None


def upload_to_storage(bucket: str, file_storage) -> str:
    """Uploads a Werkzeug FileStorage to object storage, returns its public URL."""
    client = get_s3_client()
    key = f"uploads/{uuid4()}_{file_storage.filename}"
    try:
        client.upload_fileobj(
            file_storage.stream, bucket, key, ExtraArgs={"ACL": "public-read"}
        )
        location = (
            client.get_bucket_location(Bucket=bucket)["LocationConstraint"]
            or "us-east-1"
        )
        endpoint = os.getenv("S3_PUBLIC_ENDPOINT", os.getenv("S3_ENDPOINT_URL", ""))
        if endpoint:
            # Common with MinIO or custom S3-compatible hosts
            return f"{endpoint.rstrip('/')}/{bucket}/{key}"
        # Fallback to standard AWS pattern
        return f"https://{bucket}.s3.{location}.amazonaws.com/{key}"
    except ClientError as exc:
        app.logger.exception("Failed to upload file to bucket=%s, key=%s", bucket, key)
        raise RuntimeError(f"Failed to upload file: {exc}") from exc


with app.app_context():
    db.create_all()


@app.route("/items", methods=["POST"])
def create_item():
    name = request.form.get("name")
    description = request.form.get("description")
    file_url = None

    if not name:
        return jsonify({"error": "name is required"}), 400

    if "file" in request.files:
        bucket = os.getenv("S3_BUCKET")
        if bucket:
            file_url = upload_to_storage(bucket, request.files["file"])

    item = Item(name=name, description=description, file_url=file_url)
    db.session.add(item)
    db.session.commit()
    app.logger.info("Created item id=%s name=%s", item.id, item.name)
    return jsonify(item.to_dict()), 201


@app.route("/items", methods=["GET"])
def list_items():
    items = Item.query.all()
    app.logger.info("Listed %d items", len(items))
    return jsonify([i.to_dict() for i in items])


@app.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id: int):
    item = Item.query.get_or_404(item_id)
    app.logger.info("Fetched item id=%s", item.id)
    return jsonify(item.to_dict())


@app.route("/items/<int:item_id>", methods=["PUT", "PATCH"])
def update_item(item_id: int):
    item = Item.query.get_or_404(item_id)
    data = request.form if request.form else request.json

    if not data:
        return jsonify({"error": "no data provided"}), 400

    if "name" in data:
        item.name = data["name"]
    if "description" in data:
        item.description = data["description"]

    if "file" in request.files:
        item.file_url = upload_to_storage(os.getenv("S3_BUCKET"), request.files["file"])

    db.session.commit()
    app.logger.info("Updated item id=%s", item.id)
    return jsonify(item.to_dict())


@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id: int):
    item = Item.query.get_or_404(item_id)
    bucket = os.getenv("S3_BUCKET")
    
    # Удаляем файл из Object Storage перед удалением записи из БД
    if item.file_url and bucket:
        key = extract_key_from_url(item.file_url, bucket)
        if key:
            try:
                client = get_s3_client()
                client.delete_object(Bucket=bucket, Key=key)
                app.logger.info("Deleted object from bucket=%s, key=%s", bucket, key)
            except ClientError as exc:
                app.logger.exception("Failed to delete object from bucket=%s, key=%s: %s", bucket, key, exc)
                # Продолжаем удаление записи из БД даже если не удалось удалить файл
    
    db.session.delete(item)
    db.session.commit()
    app.logger.info("Deleted item id=%s from database", item_id)
    return jsonify({"status": "deleted"})


@app.errorhandler(Exception)
def handle_exceptions(err):
    if isinstance(err, HTTPException):
        app.logger.error("HTTP error %s: %s", err.code, err.description)
        return err
    app.logger.exception("Unhandled error")
    return jsonify({"error": "internal server error"}), 500


@app.route("/", methods=["GET"])
def index_page():
    # Простейшая HTML-страница для наглядного теста CRUD.
    return """
<!doctype html>
<html lang="ru">
<head>
  <meta charset="UTF-8" />
  <title>Items CRUD</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; max-width: 900px; }
    form { margin-bottom: 16px; padding: 12px; border: 1px solid #ddd; border-radius: 6px; }
    input, textarea { width: 100%; margin: 4px 0 8px; padding: 6px; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background: #f6f6f6; }
    button { padding: 6px 10px; margin-right: 4px; }
    .actions { white-space: nowrap; }
  </style>
</head>
<body>
  <h1>Items CRUD</h1>

  <form id="createForm">
    <h3>Создать Item</h3>
    <label>Имя</label>
    <input name="name" required />
    <label>Описание</label>
    <textarea name="description"></textarea>
    <label>Файл (опционально)</label>
    <input type="file" name="file" />
    <button type="submit">Создать</button>
  </form>

  <table id="itemsTable">
    <thead>
      <tr><th>ID</th><th>Name</th><th>Description</th><th>File URL</th><th class="actions">Actions</th></tr>
    </thead>
    <tbody></tbody>
  </table>

  <script>
    const api = (path, options = {}) => fetch(path, options).then(async (res) => {
      if (!res.ok) throw new Error(await res.text() || res.statusText);
      return res.json();
    });

    async function loadItems() {
      const items = await api('/items');
      const tbody = document.querySelector('#itemsTable tbody');
      tbody.innerHTML = '';
      items.forEach(item => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td>${item.id}</td>
          <td>${item.name}</td>
          <td>${item.description || ''}</td>
          <td>${item.file_url ? '<a href="' + item.file_url + '" target="_blank">link</a>' : ''}</td>
          <td class="actions">
            <button data-action="edit" data-id="${item.id}">Edit</button>
            <button data-action="delete" data-id="${item.id}">Delete</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }

    document.getElementById('createForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const form = e.target;
      const formData = new FormData(form);
      try {
        await api('/items', { method: 'POST', body: formData });
        form.reset();
        await loadItems();
      } catch (err) {
        alert('Create error: ' + err.message);
      }
    });

    document.querySelector('#itemsTable').addEventListener('click', async (e) => {
      if (e.target.tagName !== 'BUTTON') return;
      const action = e.target.dataset.action;
      const id = e.target.dataset.id;
      if (action === 'delete') {
        if (!confirm('Удалить item #' + id + '?')) return;
        try {
          await api('/items/' + id, { method: 'DELETE' });
          await loadItems();
        } catch (err) {
          alert('Delete error: ' + err.message);
        }
      }
      if (action === 'edit') {
        const name = prompt('Новое имя?');
        if (name === null) return;
        const description = prompt('Новое описание? (пусто чтобы очистить)');
        const data = new FormData();
        data.append('name', name);
        data.append('description', description || '');
        try {
          await api('/items/' + id, { method: 'PATCH', body: data });
          await loadItems();
        } catch (err) {
          alert('Update error: ' + err.message);
        }
      }
    });

    loadItems();
  </script>
</body>
</html>
    """


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
