import logging

from constants import STATUS_PEDIDO_APROVADO, STATUS_PEDIDO_CANCELADO, STATUS_PEDIDO_PADRAO, STATUS_PEDIDO_VALIDOS
from errors import ValidationError
from models import pedido_model, produto_model

logger = logging.getLogger(__name__)


def _validar_e_calcular_itens(itens):
    total = 0
    itens_validados = []

    for item in itens:
        produto = produto_model.get_produto_por_id(item["produto_id"])
        if produto is None:
            raise ValidationError(f"Produto {item['produto_id']} não encontrado")
        if produto["estoque"] < item["quantidade"]:
            raise ValidationError(f"Estoque insuficiente para {produto['nome']}")

        total += produto["preco"] * item["quantidade"]
        itens_validados.append({
            "produto_id": item["produto_id"],
            "quantidade": item["quantidade"],
            "preco_unitario": produto["preco"],
        })

    return itens_validados, total


def _notificar_novo_pedido(pedido_id, usuario_id):
    logger.info("ENVIANDO EMAIL: Pedido %s criado para usuario %s", pedido_id, usuario_id)
    logger.info("ENVIANDO SMS: Seu pedido foi recebido!")
    logger.info("ENVIANDO PUSH: Novo pedido recebido pelo sistema")


def criar_pedido(usuario_id, itens):
    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens:
        raise ValidationError("Pedido deve ter pelo menos 1 item")

    itens_validados, total = _validar_e_calcular_itens(itens)

    pedido_id = pedido_model.criar_pedido_registro(usuario_id, STATUS_PEDIDO_PADRAO, total)
    for item in itens_validados:
        pedido_model.criar_item_pedido(
            pedido_id, item["produto_id"], item["quantidade"], item["preco_unitario"]
        )
        produto_model.decrementar_estoque(item["produto_id"], item["quantidade"])

    _notificar_novo_pedido(pedido_id, usuario_id)

    return {"pedido_id": pedido_id, "total": total}


def listar_pedidos_usuario(usuario_id):
    return pedido_model.get_pedidos_usuario(usuario_id)


def listar_todos_pedidos():
    return pedido_model.get_todos_pedidos()


def atualizar_status_pedido(pedido_id, novo_status):
    if novo_status not in STATUS_PEDIDO_VALIDOS:
        raise ValidationError("Status inválido")

    pedido_model.atualizar_status_pedido(pedido_id, novo_status)

    if novo_status == STATUS_PEDIDO_APROVADO:
        logger.info("NOTIFICAÇÃO: Pedido %s foi aprovado! Preparar envio.", pedido_id)
    if novo_status == STATUS_PEDIDO_CANCELADO:
        logger.info("NOTIFICAÇÃO: Pedido %s cancelado. Devolver estoque.", pedido_id)
