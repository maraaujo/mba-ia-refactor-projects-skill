from models import pedido_model, produto_model, usuario_model

VERSAO_API = "1.0.0"


def obter_status():
    return {
        "status": "ok",
        "database": "connected",
        "counts": {
            "produtos": produto_model.contar_produtos(),
            "usuarios": usuario_model.contar_usuarios(),
            "pedidos": pedido_model.contar_pedidos(),
        },
        "versao": VERSAO_API,
    }
