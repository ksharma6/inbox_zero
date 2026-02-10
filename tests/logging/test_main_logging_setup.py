import importlib
import logging
from logging.handlers import TimedRotatingFileHandler


def test_main_logging_setup(tmp_path, monkeypatch):
    """
    Test logging setup in main.py
    """
    log_path = tmp_path / "app.log"
    monkeypatch.setenv("LOG_FILE", str(log_path))

    import main

    importlib.reload(main)

    root = logging.getLogger()

    assert root.level == logging.INFO

    handlers = [h for h in root.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert len(handlers) >= 1

    handler = handlers[0]

    assert handler.baseFilename == str(log_path)

    assert handler.when == "MIDNIGHT"
    assert handler.backupCount == 30

    fmt = handler.formatter
    assert fmt is not None
    assert fmt._fmt == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    assert fmt.datefmt == "%Y-%m-%dT%H:%M:%S%z"
