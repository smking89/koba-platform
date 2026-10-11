"""Structured operation logging. Every CLI command run gets its own log
file capturing command/args/timing/output/errors — failures are recorded,
never hidden."""
import datetime
import json
import os

from core.config import PROJECT_ROOT

LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")


class OperationLog:
    """Use as a context manager around one CLI command's execution:

        with OperationLog("create", args={"name": "Casino"}) as log:
            log.info("starting generation")
            ... do work ...
            log.record_file("projects/casino/project.json")

    On exception, the error is recorded and re-raised — never swallowed.
    """

    def __init__(self, command, args=None):
        self.command = command
        # argparse.Namespace commonly carries a non-serializable `func`
        # callback in vars(args) — drop it rather than crash the logger.
        self.args = {k: v for k, v in (args or {}).items() if k != "func"}
        self.started_at = None
        self.ended_at = None
        self.events = []
        self.generated_files = []
        self.errors = []
        self.warnings = []

    def __enter__(self):
        self.started_at = datetime.datetime.now(datetime.timezone.utc)
        os.makedirs(LOGS_DIR, exist_ok=True)
        ts = self.started_at.strftime("%Y-%m-%d_%H%M%S")
        self.path = os.path.join(LOGS_DIR, f"{ts}_{self.command}.log")
        self.info(f"command: {self.command} args: {self.args}")
        return self

    def info(self, message):
        self.events.append({"level": "INFO", "message": message,
                             "time": datetime.datetime.now(datetime.timezone.utc).isoformat()})

    def warn(self, message):
        self.warnings.append(message)
        self.events.append({"level": "WARN", "message": message,
                             "time": datetime.datetime.now(datetime.timezone.utc).isoformat()})

    def error(self, message):
        self.errors.append(message)
        self.events.append({"level": "ERROR", "message": message,
                             "time": datetime.datetime.now(datetime.timezone.utc).isoformat()})

    def record_file(self, path):
        self.generated_files.append(path)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ended_at = datetime.datetime.now(datetime.timezone.utc)
        if exc_type is not None:
            self.error(f"{exc_type.__name__}: {exc_val}")

        record = {
            "command": self.command,
            "args": self.args,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
            "duration_seconds": (self.ended_at - self.started_at).total_seconds(),
            "events": self.events,
            "generated_files": self.generated_files,
            "errors": self.errors,
            "warnings": self.warnings,
            "success": exc_type is None and not self.errors,
        }
        with open(self.path, "w") as f:
            json.dump(record, f, indent=2, default=str)

        return False  # never swallow the exception


def list_recent_logs(limit=20):
    os.makedirs(LOGS_DIR, exist_ok=True)
    files = sorted(
        (f for f in os.listdir(LOGS_DIR) if f.endswith(".log")),
        reverse=True,
    )
    return [os.path.join(LOGS_DIR, f) for f in files[:limit]]
