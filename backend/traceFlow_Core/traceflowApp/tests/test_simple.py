import pytest
import sys
import os

def test_import_traceflowApp():
    """Prueba simple para verificar que se puede importar traceflowApp"""
    import traceflowApp
    assert traceflowApp is not None

def test_python_path():
    """Prueba que muestra el PYTHONPATH actual (útil para debug)"""
    print("\nPython path:", sys.path)
    assert True