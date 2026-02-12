"""Módulo do servidor de autenticação"""

from .auth_server import (
    run_server_thread,
    wait_for_auth_code,
    CallbackHandler
)
from .html_templates import SUCCESS_PAGE, ERROR_PAGE

__all__ = [
    'run_server_thread',
    'wait_for_auth_code',
    'CallbackHandler',
    'SUCCESS_PAGE',
    'ERROR_PAGE'
]