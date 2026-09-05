import logging

from flask import Flask, jsonify
from flask_cors import CORS

import database
from config import Config
from errors import register_error_handlers
from routes import register_routes


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    if app.config.get("SECRET_KEY_IS_GENERATED"):
        app.logger.warning(
            "SECRET_KEY não definida via variável de ambiente; usando chave gerada "
            "aleatoriamente para esta execução (sessões não sobrevivem a um restart)."
        )
    if not app.config.get("ADMIN_TOKEN"):
        app.logger.warning(
            "ADMIN_TOKEN não configurado; o endpoint /admin/reset-db ficará inacessível."
        )

    CORS(app, origins=app.config["CORS_ORIGINS"])

    database.init_app(app)
    register_error_handlers(app)
    register_routes(app)

    @app.route("/")
    def index():
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": "1.0.0",
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        })

    return app


if __name__ == "__main__":
    app = create_app()
    app.logger.info("=" * 50)
    app.logger.info("SERVIDOR INICIADO")
    app.logger.info("Rodando em http://localhost:%s", app.config["PORT"])
    app.logger.info("=" * 50)
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["DEBUG"])
