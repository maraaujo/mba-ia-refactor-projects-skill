from functools import wraps

from flask import current_app, request

from errors import ForbiddenError


def admin_required(view):
    """Exige o header X-Admin-Token com valor igual a ADMIN_TOKEN configurado."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        token_configurado = current_app.config.get("ADMIN_TOKEN")
        token_recebido = request.headers.get("X-Admin-Token")

        if not token_configurado or token_recebido != token_configurado:
            raise ForbiddenError("Acesso administrativo não autorizado")

        return view(*args, **kwargs)

    return wrapper
