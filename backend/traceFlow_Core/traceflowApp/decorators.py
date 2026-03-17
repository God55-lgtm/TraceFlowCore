import functools
from . import context  # para acceder al span activo

def trace_attribute(**kwargs):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs_func):
            # Aquí puedes acceder al span activo desde el request o thread local
            # y añadir los atributos
            return func(*args, **kwargs_func)
        return wrapper
    return decorator