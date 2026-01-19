import importlib
import logging
import os
from logging.handlers import TimedRotatingFileHandler

import pytest


def test_main_logging_setup():
    """
    Test logging setup in main.py
    """
    log_path = os.getenv("LOG_FILE") + "app.log"
    pytest.monkeypatch.setenv("LOG_FILE", log_path)

    import main
