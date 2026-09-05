from flask import jsonify, request

from services import produto_service


def listar_produtos():
    produtos = produto_service.listar_produtos()
    return jsonify({"dados": produtos, "sucesso": True}), 200


def buscar_produto(id):
    produto = produto_service.buscar_produto(id)
    return jsonify({"dados": produto, "sucesso": True}), 200


def criar_produto():
    dados = request.get_json(silent=True)
    produto_id = produto_service.criar_produto(dados)
    return jsonify({"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}), 201


def atualizar_produto(id):
    dados = request.get_json(silent=True)
    produto_service.atualizar_produto(id, dados)
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


def deletar_produto(id):
    produto_service.deletar_produto(id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200


def buscar_produtos():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria", None)
    preco_min = request.args.get("preco_min", None)
    preco_max = request.args.get("preco_max", None)

    resultados = produto_service.buscar_produtos(termo, categoria, preco_min, preco_max)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200
