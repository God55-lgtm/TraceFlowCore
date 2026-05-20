import functools
from . import context

def trace_attribute(**attrs):
    """
    Decorador para añadir atributos al span activo durante la ejecución de una función.
    Uso: @trace_attribute(user_id=123, action='purchase')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Añadir los atributos especificados
            for key, value in attrs.items():
                context.add_attribute(key, value)
            return func(*args, **kwargs)
        return wrapper
    return decorator

# También puedes proporcionar una función directa para uso imperativo
def add_attribute(key, value):
    context.add_attribute(key, value)