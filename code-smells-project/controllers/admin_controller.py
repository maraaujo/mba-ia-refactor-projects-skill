from flask import jsonify

import database
from middleware import admin_required


@admin_required
def reset_database():
    database.reset_database()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200


def executar_query_desabilitado():
    """Endpoint legado mantido apenas para compatibilidade de contrato.

    Nunca lê ou processa o corpo da requisição, e nunca executa SQL — a
    funcionalidade original (execução de SQL arbitrário vindo do cliente)
    foi permanentemente desabilitada por representar risco crítico de
    segurança (ver finding C2 do relatório de auditoria).
    """
    return jsonify({
        "erro": "Endpoint desabilitado por motivos de segurança. Execução de SQL arbitrário não é mais suportada.",
        "sucesso": False,
    }), 410
