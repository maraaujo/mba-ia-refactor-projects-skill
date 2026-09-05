from sqlalchemy import func

from database import db
from errors import NotFoundError, ValidationError
from models.category import Category
from models.task import Task
from utils.helpers import DEFAULT_COLOR


def list_categories():
    task_counts = dict(
        db.session.query(Task.category_id, func.count(Task.id))
        .group_by(Task.category_id)
        .all()
    )

    result = []
    for c in Category.query.all():
        data = c.to_dict()
        data['task_count'] = task_counts.get(c.id, 0)
        result.append(data)
    return result


def create_category(data):
    if not data:
        raise ValidationError('Dados inválidos')

    name = data.get('name')
    if not name:
        raise ValidationError('Nome é obrigatório')

    category = Category(
        name=name,
        description=data.get('description', ''),
        color=data.get('color', DEFAULT_COLOR),
    )

    db.session.add(category)
    db.session.commit()
    return category.to_dict()


def update_category(cat_id, data):
    category = db.session.get(Category, cat_id)
    if not category:
        raise NotFoundError('Categoria não encontrada')
    if not data:
        raise ValidationError('Dados inválidos')

    if 'name' in data:
        category.name = data['name']
    if 'description' in data:
        category.description = data['description']
    if 'color' in data:
        category.color = data['color']

    db.session.commit()
    return category.to_dict()


def delete_category(cat_id):
    category = db.session.get(Category, cat_id)
    if not category:
        raise NotFoundError('Categoria não encontrada')

    db.session.delete(category)
    db.session.commit()
