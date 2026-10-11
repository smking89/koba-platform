"""Thin logging wrapper so framework messages are consistent and greppable
in Blender's console output."""
import sys
import time


def _emit(level, msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", file=sys.stderr)


def info(msg):
    _emit("INFO", msg)


def warn(msg):
    _emit("WARN", msg)


def error(msg):
    _emit("ERROR", msg)
