from flask import jsonify, request

from services import usuario_service


def listar_usuarios():
    usuarios = usuario_service.listar_usuarios()
    return jsonify({"dados": usuarios, "sucesso": True}), 200


def buscar_usuario(id):
    usuario = usuario_service.buscar_usuario(id)
    return jsonify({"dados": usuario, "sucesso": True}), 200


def criar_usuario():
    dados = request.get_json(silent=True)
    usuario_id = usuario_service.criar_usuario(dados)
    return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201


def login():
    dados = request.get_json(silent=True) or {}
    usuario = usuario_service.autenticar(dados.get("email", ""), dados.get("senha", ""))
    return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200
