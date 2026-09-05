from flask import jsonify

from services import health_service


def health_check():
    return jsonify(health_service.obter_status()), 200
