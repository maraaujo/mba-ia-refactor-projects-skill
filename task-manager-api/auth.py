from functools import wraps

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from database import db
from errors import AuthError, ForbiddenError
from models.user import User


def _serializer():
    return URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt='auth-token')


def generate_token(user_id):
    return _serializer().dumps({'user_id': user_id})


def verify_token(token):
    max_age = current_app.config.get('TOKEN_MAX_AGE_SECONDS', 86400)
    try:
        data = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    return data.get('user_id')


def _authenticate():
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        raise AuthError('Token de autenticação ausente ou inválido')

    user_id = verify_token(auth_header[len('Bearer '):])
    if not user_id:
        raise AuthError('Token de autenticação ausente ou inválido')

    user = db.session.get(User, user_id)
    if not user or not user.active:
        raise AuthError('Token de autenticação ausente ou inválido')

    return user


def require_auth(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        g.current_user = _authenticate()
        return view(*args, **kwargs)
    return wrapper


def require_admin(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = _authenticate()
        if not user.is_admin():
            raise ForbiddenError('Acesso restrito a administradores')
        g.current_user = user
        return view(*args, **kwargs)
    return wrapper
