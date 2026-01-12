"""Инициализация Flask приложения."""
import logging
import os

from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

db = SQLAlchemy()


def create_app():
    """Фабрика приложения Flask."""
    app = Flask(__name__)

    # Конфигурация
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'app.db')}",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv(
        "SECRET_KEY", "dev-secret-key-change-in-production"
    )

    # Инициализация расширений
    db.init_app(app)

    # Регистрация маршрутов
    from app.routes import auth_routes, items_routes, iam_routes, main_routes

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(items_routes.bp)
    app.register_blueprint(iam_routes.bp)
    app.register_blueprint(main_routes.bp)
    
    # Регистрируем /init-test-users на корневом уровне
    from app.routes.iam_routes import init_test_users
    app.add_url_rule("/init-test-users", "init_test_users", init_test_users, methods=["POST"])

    # Обработчик ошибок
    from app.utils.error_handlers import register_error_handlers

    register_error_handlers(app)

    # Инициализация БД
    with app.app_context():
        db.create_all()
        from app.models.role import Role

        # Создаём роли по умолчанию, если их нет
        if Role.query.count() == 0:
            roles = [
                Role(name="admin", description="Full access to all resources"),
                Role(name="user", description="Can create and manage own items"),
                Role(name="guest", description="Read-only access"),
            ]
            for role in roles:
                db.session.add(role)
            db.session.commit()
            app.logger.info("Created default roles: admin, user, guest")

    return app
