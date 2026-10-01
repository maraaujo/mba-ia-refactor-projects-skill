import logging

from constants import (
    QUANTIDADE_MINIMA_ITEM,
    STATUS_PEDIDO_APROVADO,
    STATUS_PEDIDO_CANCELADO,
    STATUS_PEDIDO_PADRAO,
    STATUS_PEDIDO_VALIDOS,
)
from errors import ValidationError
from models import pedido_model, produto_model

logger = logging.getLogger(__name__)


def _eh_inteiro(valor):
    # bool é subclasse de int em Python; True/False não são quantidades válidas.
    return isinstance(valor, int) and not isinstance(valor, bool)


def _validar_formato_itens(itens):
    if not isinstance(itens, list):
        raise ValidationError("Itens devem ser uma lista")

    for item in itens:
        if not isinstance(item, dict):
            raise ValidationError("Cada item deve conter produto_id e quantidade")
        if not _eh_inteiro(item.get("produto_id")):
            raise ValidationError("produto_id deve ser um número inteiro")
        if not _eh_inteiro(item.get("quantidade")) or item["quantidade"] < QUANTIDADE_MINIMA_ITEM:
            raise ValidationError(f"Quantidade deve ser um inteiro maior ou igual a {QUANTIDADE_MINIMA_ITEM}")


def _validar_e_calcular_itens(itens):
    total = 0
    itens_validados = []
    produtos = produto_model.get_produtos_por_ids([item["produto_id"] for item in itens])

    for item in itens:
        produto = produtos.get(item["produto_id"])
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

    _validar_formato_itens(itens)
    itens_validados, total = _validar_e_calcular_itens(itens)

    pedido_id = pedido_model.registrar_pedido(usuario_id, STATUS_PEDIDO_PADRAO, total, itens_validados)

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
