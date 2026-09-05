from datetime import datetime, timezone
import re
import uuid

VALID_STATUSES = ['pending', 'in_progress', 'done', 'cancelled']
VALID_ROLES = ['user', 'admin', 'manager']
MAX_TITLE_LENGTH = 200
MIN_TITLE_LENGTH = 3
MIN_PASSWORD_LENGTH = 4
DEFAULT_PRIORITY = 3
DEFAULT_COLOR = '#000000'
MIN_PRIORITY = 1
MAX_PRIORITY = 5


def utc_now():
    """Substitui datetime.utcnow() (deprecated desde Python 3.12) mantendo datetimes naive/UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def format_date(date_obj):
    if date_obj:
        return str(date_obj)
    return None


def calculate_percentage(part, total):
    if total == 0:
        return 0
    return round((part / total) * 100, 2)


def validate_email(email):
    if re.match(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$', email):
        return True
    return False


def sanitize_string(s):
    if s:
        return s.strip()
    return s


def generate_id():
    return str(uuid.uuid4())


def log_action(action, details=None):
    timestamp = utc_now()
    print(f"[{timestamp}] ACTION: {action}")
    if details:
        print(f"  DETAILS: {details}")


def parse_date(date_string):
    try:
        return datetime.strptime(date_string, '%Y-%m-%d')
    except ValueError:
        try:
            return datetime.strptime(date_string, '%d/%m/%Y')
        except ValueError:
            return None


def is_valid_color(color):
    if color and len(color) == 7 and color[0] == '#':
        return True
    return False


def process_task_data(data, existing_task=None):
    """Valida e normaliza os campos de uma task recebidos via JSON.

    Retorna (result, error): result é um dict só com os campos presentes em
    `data`; error é uma mensagem de validação ou None em caso de sucesso.
    """
    result = {}

    if 'title' in data:
        title = data['title']
        if title:
            title = title.strip()
            if len(title) < MIN_TITLE_LENGTH:
                return None, 'Título muito curto'
            if len(title) > MAX_TITLE_LENGTH:
                return None, 'Título muito longo'
            result['title'] = title
        else:
            return None, 'Título não pode ser vazio'

    if 'description' in data:
        result['description'] = data['description']

    if 'status' in data:
        if data['status'] in VALID_STATUSES:
            result['status'] = data['status']
        else:
            return None, 'Status inválido'

    if 'priority' in data:
        try:
            p = int(data['priority'])
        except (TypeError, ValueError):
            return None, 'Prioridade inválida'

        if MIN_PRIORITY <= p <= MAX_PRIORITY:
            result['priority'] = p
        else:
            return None, 'Prioridade deve ser entre 1 e 5'

    if 'due_date' in data:
        if data['due_date']:
            parsed = parse_date(data['due_date'])
            if parsed:
                result['due_date'] = parsed
            else:
                return None, 'Formato de data inválido. Use YYYY-MM-DD'
        else:
            result['due_date'] = None

    if 'tags' in data:
        tags = data['tags']
        if isinstance(tags, list):
            result['tags'] = ','.join(tags)
        else:
            result['tags'] = tags

    return result, None
