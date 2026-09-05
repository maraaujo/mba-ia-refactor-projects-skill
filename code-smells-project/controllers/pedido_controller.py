from flask import jsonify, request

from errors import ValidationError
from services import pedido_service


def criar_pedido():
    dados = request.get_json(silent=True)
    if not dados:
        raise ValidationError("Dados inválidos")

    resultado = pedido_service.criar_pedido(dados.get("usuario_id"), dados.get("itens", []))
    return jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}), 201


def listar_pedidos_usuario(usuario_id):
    pedidos = pedido_service.listar_pedidos_usuario(usuario_id)
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def listar_todos_pedidos():
    pedidos = pedido_service.listar_todos_pedidos()
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def atualizar_status_pedido(pedido_id):
    dados = request.get_json(silent=True) or {}
    pedido_service.atualizar_status_pedido(pedido_id, dados.get("status", ""))
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
