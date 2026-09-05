from flask import Blueprint, jsonify, request

from auth import require_admin
from services import user_service

user_bp = Blueprint('users', __name__)


@user_bp.route('/users', methods=['GET'])
def get_users():
    return jsonify(user_service.list_users()), 200


@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    return jsonify(user_service.get_user_with_tasks(user_id)), 200


@user_bp.route('/users', methods=['POST'])
def create_user():
    user = user_service.create_user(request.get_json())
    return jsonify(user), 201


@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = user_service.update_user(user_id, request.get_json())
    return jsonify(user), 200


@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user_id):
    user_service.delete_user(user_id)
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


@user_bp.route('/users/<int:user_id>/tasks', methods=['GET'])
def get_user_tasks(user_id):
    return jsonify(user_service.get_user_tasks(user_id)), 200


@user_bp.route('/login', methods=['POST'])
def login():
    result = user_service.login(request.get_json())
    return jsonify(result), 200
