"""Constantes de domínio compartilhadas entre services e controllers."""

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
CATEGORIA_PADRAO = "geral"

STATUS_PEDIDO_VALIDOS = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]
STATUS_PEDIDO_PADRAO = "pendente"
STATUS_PEDIDO_APROVADO = "aprovado"
STATUS_PEDIDO_CANCELADO = "cancelado"

NOME_PRODUTO_TAMANHO_MINIMO = 2
NOME_PRODUTO_TAMANHO_MAXIMO = 200

FAIXA_DESCONTO_ALTA = 10000
FAIXA_DESCONTO_MEDIA = 5000
FAIXA_DESCONTO_BAIXA = 1000
PERCENTUAL_DESCONTO_ALTA = 0.10
PERCENTUAL_DESCONTO_MEDIA = 0.05
PERCENTUAL_DESCONTO_BAIXA = 0.02
