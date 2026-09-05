import sqlite3

from flask import current_app, g

import schema


def _connect(database_path):
    conn = sqlite3.connect(database_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """Retorna a conexão de banco associada ao contexto da requisição atual."""
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    """Registra o teardown de conexão e garante schema/dados iniciais."""
    app.teardown_appcontext(close_db)

    with app.app_context():
        conn = _connect(app.config["DATABASE_PATH"])
        try:
            schema.criar_schema(conn)
            schema.popular_dados_iniciais(conn)
        finally:
            conn.close()


def reset_database():
    """Remove todos os registros das tabelas principais. Uso administrativo."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM itens_pedido")
    cursor.execute("DELETE FROM pedidos")
    cursor.execute("DELETE FROM produtos")
    cursor.execute("DELETE FROM usuarios")
    db.commit()
