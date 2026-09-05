"""Acesso a dados de pedidos. Sem regras de negócio, apenas queries parametrizadas."""

from database import get_db


def _montar_pedidos_a_partir_das_linhas(rows):
    """Agrupa o resultado de uma única query com JOIN em uma lista de pedidos com itens."""
    pedidos_por_id = {}
    ordem = []

    for row in rows:
        pedido_id = row["pedido_id"]
        if pedido_id not in pedidos_por_id:
            pedidos_por_id[pedido_id] = {
                "id": pedido_id,
                "usuario_id": row["usuario_id"],
                "status": row["status"],
                "total": row["total"],
                "criado_em": row["criado_em"],
                "itens": [],
            }
            ordem.append(pedido_id)

        if row["produto_id"] is not None:
            pedidos_por_id[pedido_id]["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"] or "Desconhecido",
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })

    return [pedidos_por_id[pedido_id] for pedido_id in ordem]


_QUERY_PEDIDOS_COM_ITENS = """
    SELECT
        p.id AS pedido_id,
        p.usuario_id AS usuario_id,
        p.status AS status,
        p.total AS total,
        p.criado_em AS criado_em,
        ip.produto_id AS produto_id,
        ip.quantidade AS quantidade,
        ip.preco_unitario AS preco_unitario,
        pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido ip ON ip.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = ip.produto_id
"""


def get_pedidos_usuario(usuario_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        _QUERY_PEDIDOS_COM_ITENS + " WHERE p.usuario_id = ? ORDER BY p.id",
        (usuario_id,),
    )
    return _montar_pedidos_a_partir_das_linhas(cursor.fetchall())


def get_todos_pedidos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute(_QUERY_PEDIDOS_COM_ITENS + " ORDER BY p.id")
    return _montar_pedidos_a_partir_das_linhas(cursor.fetchall())


def criar_pedido_registro(usuario_id, status, total):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
        (usuario_id, status, total),
    )
    db.commit()
    return cursor.lastrowid


def criar_item_pedido(pedido_id, produto_id, quantidade, preco_unitario):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
        (pedido_id, produto_id, quantidade, preco_unitario),
    )
    db.commit()


def atualizar_status_pedido(pedido_id, novo_status):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE pedidos SET status = ? WHERE id = ?",
        (novo_status, pedido_id),
    )
    db.commit()


def contar_pedidos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM pedidos")
    return cursor.fetchone()[0]


def somar_faturamento():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT SUM(total) FROM pedidos")
    faturamento = cursor.fetchone()[0]
    return faturamento if faturamento is not None else 0


def contar_pedidos_por_status(status):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE status = ?", (status,))
    return cursor.fetchone()[0]
