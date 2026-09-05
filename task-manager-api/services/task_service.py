from sqlalchemy.orm import joinedload

from database import db
from errors import NotFoundError, ValidationError
from models.category import Category
from models.task import Task
from models.user import User
from utils.helpers import DEFAULT_PRIORITY, process_task_data, utc_now


def _serialize(task):
    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    data['user_name'] = task.user.name if task.user else None
    data['category_name'] = task.category.name if task.category else None
    return data


def list_tasks():
    tasks = (
        Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
    )
    return [_serialize(t) for t in tasks]


def get_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    return _serialize(task)


def _check_references(user_id, category_id):
    if user_id and not db.session.get(User, user_id):
        raise NotFoundError('Usuário não encontrado')
    if category_id and not db.session.get(Category, category_id):
        raise NotFoundError('Categoria não encontrada')


def create_task(data):
    if not data:
        raise ValidationError('Dados inválidos')
    if not data.get('title'):
        raise ValidationError('Título é obrigatório')

    result, error = process_task_data(data)
    if error:
        raise ValidationError(error)

    user_id = data.get('user_id')
    category_id = data.get('category_id')
    _check_references(user_id, category_id)

    task = Task(
        title=result['title'],
        description=result.get('description', data.get('description', '')),
        status=result.get('status', 'pending'),
        priority=result.get('priority', DEFAULT_PRIORITY),
        user_id=user_id,
        category_id=category_id,
        due_date=result.get('due_date'),
        tags=result.get('tags'),
    )

    db.session.add(task)
    db.session.commit()
    return task.to_dict()


def update_task(task_id, data):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    if not data:
        raise ValidationError('Dados inválidos')

    result, error = process_task_data(data, existing_task=task)
    if error:
        raise ValidationError(error)

    if 'user_id' in data:
        _check_references(data['user_id'], None)
        task.user_id = data['user_id']

    if 'category_id' in data:
        _check_references(None, data['category_id'])
        task.category_id = data['category_id']

    for field in ('title', 'description', 'status', 'priority', 'due_date', 'tags'):
        if field in result:
            setattr(task, field, result[field])

    task.updated_at = utc_now()
    db.session.commit()
    return task.to_dict()


def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    db.session.delete(task)
    db.session.commit()


def search_tasks(query, status, priority, user_id):
    tasks = Task.query

    if query:
        tasks = tasks.filter(
            db.or_(Task.title.like(f'%{query}%'), Task.description.like(f'%{query}%'))
        )
    if status:
        tasks = tasks.filter(Task.status == status)
    if priority:
        tasks = tasks.filter(Task.priority == int(priority))
    if user_id:
        tasks = tasks.filter(Task.user_id == int(user_id))

    return [t.to_dict() for t in tasks.all()]


def get_stats():
    total = Task.query.count()
    pending = Task.query.filter_by(status='pending').count()
    in_progress = Task.query.filter_by(status='in_progress').count()
    done = Task.query.filter_by(status='done').count()
    cancelled = Task.query.filter_by(status='cancelled').count()
    overdue_count = sum(1 for t in Task.query.all() if t.is_overdue())

    return {
        'total': total,
        'pending': pending,
        'in_progress': in_progress,
        'done': done,
        'cancelled': cancelled,
        'overdue': overdue_count,
        'completion_rate': round((done / total) * 100, 2) if total > 0 else 0,
    }
