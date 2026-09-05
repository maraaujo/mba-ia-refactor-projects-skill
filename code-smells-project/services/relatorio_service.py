from constants import (
    FAIXA_DESCONTO_ALTA,
    FAIXA_DESCONTO_BAIXA,
    FAIXA_DESCONTO_MEDIA,
    PERCENTUAL_DESCONTO_ALTA,
    PERCENTUAL_DESCONTO_BAIXA,
    PERCENTUAL_DESCONTO_MEDIA,
    STATUS_PEDIDO_APROVADO,
    STATUS_PEDIDO_CANCELADO,
    STATUS_PEDIDO_PADRAO,
)
from models import pedido_model


def _calcular_desconto(faturamento):
    if faturamento > FAIXA_DESCONTO_ALTA:
        return faturamento * PERCENTUAL_DESCONTO_ALTA
    if faturamento > FAIXA_DESCONTO_MEDIA:
        return faturamento * PERCENTUAL_DESCONTO_MEDIA
    if faturamento > FAIXA_DESCONTO_BAIXA:
        return faturamento * PERCENTUAL_DESCONTO_BAIXA
    return 0


def gerar_relatorio_vendas():
    total_pedidos = pedido_model.contar_pedidos()
    faturamento = pedido_model.somar_faturamento()
    pendentes = pedido_model.contar_pedidos_por_status(STATUS_PEDIDO_PADRAO)
    aprovados = pedido_model.contar_pedidos_por_status(STATUS_PEDIDO_APROVADO)
    cancelados = pedido_model.contar_pedidos_por_status(STATUS_PEDIDO_CANCELADO)

    desconto = _calcular_desconto(faturamento)

    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": pendentes,
        "pedidos_aprovados": aprovados,
        "pedidos_cancelados": cancelados,
        "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
    }
