import logging
import json
import os
from uuid import uuid4
from datetime import datetime
from typing import Any, Dict

class IndustryLogger:
    """
    Structured logger that simulates industry practices.
    Logs to both console and a file in JSON format.
    """
    def __init__(self, name: str = "AI-Lab-Agent", log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        self.log_dir = log_dir
        self.session_id = datetime.utcnow().strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
        self.session_dir = os.path.join(log_dir, "sessions")

        os.makedirs(self.session_dir, exist_ok=True)

        # Avoid duplicate handlers if the module is reloaded in the same interpreter.
        if not self.logger.handlers:
            session_log_file = os.path.join(self.session_dir, f"session-{self.session_id}.log")

            file_handler = logging.FileHandler(session_log_file, encoding="utf-8")
            console_handler = logging.StreamHandler()

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)

        self.logger.info(
            json.dumps(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "event": "LOG_SESSION_START",
                    "data": {"session_id": self.session_id, "log_file": f"sessions/session-{self.session_id}.log"},
                }
            )
        )

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs an event with a timestamp and type."""
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "session_id": self.session_id,
            "data": data
        }
        self.logger.info(json.dumps(payload))

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str, exc_info=True):
        self.logger.error(msg, exc_info=exc_info)

# Global logger instance
logger = IndustryLogger()
