from flask import jsonify
from sqlalchemy.exc import SQLAlchemyError


class AppError(Exception):
    status_code = 500

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationError(AppError):
    status_code = 400


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409


class AuthError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


def register_error_handlers(app):
    from database import db

    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({'error': err.message}), err.status_code

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(err):
        db.session.rollback()
        return jsonify({'error': 'Erro interno de banco de dados'}), 500

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify({'error': 'Recurso não encontrado'}), 404

    @app.errorhandler(Exception)
    def handle_unexpected_error(err):
        db.session.rollback()
        return jsonify({'error': 'Erro interno'}), 500
