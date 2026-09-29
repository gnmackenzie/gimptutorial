"""Safe console and rotating-file logging configuration."""

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


class RedactingFilter(logging.Filter):
    """Redact common credential labels from rendered log records."""

    _labels = ("password=", "authorization=", "cookie=", "secret=")

    def filter(self, record: logging.LogRecord) -> bool:
        """Replace suspicious rendered messages.

        Args:
            record: Log record being emitted.

        Returns:
            Always True so the record remains visible.
        """
        message = record.getMessage()
        if any(label in message.lower() for label in self._labels):
            record.msg = "Sensitive log content redacted"
            record.args = ()
        return True


def configure_logging(log_directory: Path, retention_days: int) -> None:
    """Configure root logging with daily UTC rotation.

    Args:
        log_directory: Writable log directory.
        retention_days: Number of rotated files to retain.
    """
    log_directory.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)sZ %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    file_handler = TimedRotatingFileHandler(
        log_directory / "net-worth.log",
        when="midnight",
        backupCount=retention_days,
        encoding="utf-8",
        utc=True,
    )
    handlers.append(file_handler)
    for handler in handlers:
        handler.setFormatter(formatter)
        handler.addFilter(RedactingFilter())
    logging.basicConfig(level=logging.INFO, handlers=handlers, force=True)
