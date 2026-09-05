"""Acesso a dados de produtos. Sem regras de negócio, apenas queries parametrizadas."""

from database import get_db


def _row_para_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def get_todos_produtos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos")
    return [_row_para_dict(row) for row in cursor.fetchall()]


def get_produto_por_id(produto_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
    row = cursor.fetchone()
    return _row_para_dict(row) if row else None


def criar_produto(nome, descricao, preco, estoque, categoria):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        (nome, descricao, preco, estoque, categoria),
    )
    db.commit()
    return cursor.lastrowid


def atualizar_produto(produto_id, nome, descricao, preco, estoque, categoria):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
        (nome, descricao, preco, estoque, categoria, produto_id),
    )
    db.commit()


def deletar_produto(produto_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    db.commit()


def decrementar_estoque(produto_id, quantidade):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
        (quantidade, produto_id),
    )
    db.commit()


def buscar_produtos(termo=None, categoria=None, preco_min=None, preco_max=None):
    db = get_db()
    cursor = db.cursor()

    condicoes = ["1 = 1"]
    parametros = []

    if termo:
        condicoes.append("(nome LIKE ? OR descricao LIKE ?)")
        curinga = f"%{termo}%"
        parametros.extend([curinga, curinga])
    if categoria:
        condicoes.append("categoria = ?")
        parametros.append(categoria)
    if preco_min is not None:
        condicoes.append("preco >= ?")
        parametros.append(preco_min)
    if preco_max is not None:
        condicoes.append("preco <= ?")
        parametros.append(preco_max)

    query = "SELECT * FROM produtos WHERE " + " AND ".join(condicoes)
    cursor.execute(query, parametros)
    return [_row_para_dict(row) for row in cursor.fetchall()]


def contar_produtos():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) FROM produtos")
    return cursor.fetchone()[0]
