"""Обработчики ошибок."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """Регистрирует обработчики ошибок."""

    @app.errorhandler(Exception)
    def handle_exceptions(err):
        if isinstance(err, HTTPException):
            app.logger.error("HTTP error %s: %s", err.code, err.description)
            return err
        app.logger.exception("Unhandled error")
        return jsonify({"error": "internal server error"}), 500
