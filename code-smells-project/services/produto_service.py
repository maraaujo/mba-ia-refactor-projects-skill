import logging

from constants import (
    CATEGORIA_PADRAO,
    CATEGORIAS_VALIDAS,
    NOME_PRODUTO_TAMANHO_MAXIMO,
    NOME_PRODUTO_TAMANHO_MINIMO,
)
from errors import NotFoundError, ValidationError
from models import produto_model

logger = logging.getLogger(__name__)


def _validar_dados_produto(dados):
    if not dados:
        raise ValidationError("Dados inválidos")
    if "nome" not in dados:
        raise ValidationError("Nome é obrigatório")
    if "preco" not in dados:
        raise ValidationError("Preço é obrigatório")
    if "estoque" not in dados:
        raise ValidationError("Estoque é obrigatório")

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if len(nome) < NOME_PRODUTO_TAMANHO_MINIMO:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_PRODUTO_TAMANHO_MAXIMO:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError(f"Categoria inválida. Válidas: {CATEGORIAS_VALIDAS}")

    return nome, descricao, preco, estoque, categoria


def listar_produtos():
    return produto_model.get_todos_produtos()


def buscar_produto(produto_id):
    produto = produto_model.get_produto_por_id(produto_id)
    if not produto:
        raise NotFoundError("Produto não encontrado")
    return produto


def criar_produto(dados):
    nome, descricao, preco, estoque, categoria = _validar_dados_produto(dados)
    produto_id = produto_model.criar_produto(nome, descricao, preco, estoque, categoria)
    logger.info("Produto criado com ID: %s", produto_id)
    return produto_id


def atualizar_produto(produto_id, dados):
    if not produto_model.get_produto_por_id(produto_id):
        raise NotFoundError("Produto não encontrado")

    nome, descricao, preco, estoque, categoria = _validar_dados_produto(dados)
    produto_model.atualizar_produto(produto_id, nome, descricao, preco, estoque, categoria)


def deletar_produto(produto_id):
    if not produto_model.get_produto_por_id(produto_id):
        raise NotFoundError("Produto não encontrado")

    produto_model.deletar_produto(produto_id)
    logger.info("Produto %s deletado", produto_id)


def buscar_produtos(termo, categoria, preco_min, preco_max):
    if preco_min is not None:
        preco_min = float(preco_min)
    if preco_max is not None:
        preco_max = float(preco_max)

    return produto_model.buscar_produtos(termo, categoria, preco_min, preco_max)
