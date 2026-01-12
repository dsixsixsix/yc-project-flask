"""Главные маршруты приложения."""
import os

from flask import Blueprint, render_template

bp = Blueprint("main", __name__)


@bp.route("/", methods=["GET"])
def index_page():
    """Главная страница с веб-интерфейсом."""
    # Читаем HTML из файла
    html_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "templates", "index.html"
    )
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()
