import contextvars
from typing import Dict, Any

# Variable de contexto que almacena los atributos del span actual
_span_attributes: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar('span_attributes', default={})

def add_attribute(key: str, value: Any) -> None:
    """Añade un atributo al span activo."""
    attrs = _span_attributes.get()
    attrs[key] = value
    _span_attributes.set(attrs)

def get_attributes() -> Dict[str, Any]:
    """Devuelve todos los atributos del span activo."""
    return _span_attributes.get().copy()

def clear_attributes() -> None:
    """Limpia los atributos (al finalizar el span)."""
    _span_attributes.set({})