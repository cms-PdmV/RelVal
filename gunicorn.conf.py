"""
Gunicorn WSGI server configuration
For details about configuration precedence,
please see: https://docs.gunicorn.org/en/stable/configure.html
"""
import multiprocessing
import os
from core.utils.cli import parse_bool
from app import set_app

mode = os.environ.get("MODE", "dev")
debug = parse_bool(os.environ.get("DEBUG", True))
host, port, debug = set_app(mode=mode, debug=debug)
bind = f"{host}:{port}"
workers = multiprocessing.cpu_count() * 2 + 1
