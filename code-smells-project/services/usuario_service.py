import logging

from werkzeug.security import check_password_hash, generate_password_hash

from errors import AuthError, NotFoundError, ValidationError
from models import usuario_model

logger = logging.getLogger(__name__)


def listar_usuarios():
    return usuario_model.get_todos_usuarios()


def buscar_usuario(usuario_id):
    usuario = usuario_model.get_usuario_por_id(usuario_id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return usuario


def criar_usuario(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")

    senha_hash = generate_password_hash(senha)
    usuario_id = usuario_model.criar_usuario(nome, email, senha_hash)
    logger.info("Usuário criado: %s", email)
    return usuario_id


def autenticar(email, senha):
    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")

    usuario = usuario_model.get_usuario_com_senha_por_email(email)
    if not usuario or not check_password_hash(usuario["senha"], senha):
        logger.info("Login falhou: %s", email)
        raise AuthError("Email ou senha inválidos")

    logger.info("Login bem-sucedido: %s", email)
    return {
        "id": usuario["id"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "tipo": usuario["tipo"],
    }
