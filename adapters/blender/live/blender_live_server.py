"""Live-bridge bootstrap. Run ONCE, inside a normally-launched (non -b) GUI
Blender, via:

    blender --python live/blender_live_server.py

This starts a small local TCP server on a background thread and drains
incoming code through bpy.app.timers on Blender's main thread — required
because bpy is not thread-safe from arbitrary Python threads. The GUI
event loop keeps running exactly as normal; this only adds a listener.

Protocol: a client opens a TCP connection, writes UTF-8 Python source,
half-closes the socket (shutdown(SHUT_WR)) to signal end-of-code, then
reads the response until the server closes the connection. The response
is:

    OK|ERROR
    --OUT--
    <captured stdout>
    --ERR--
    <captured stderr / traceback>
    --END--

Execution uses one persistent namespace across calls (like a REPL), so
variables/objects created in one call (e.g. an Asset) are still available
in the next one. This is intentional: it's what makes staged, incremental
generation possible per the interactive workflow.
"""
import contextlib
import importlib
import io
import queue
import socket
import sys
import threading
import traceback

import bpy

PROJECT_ROOT = "/home/koba/Desktop/koba_creator_engine/adapters/blender"

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.blender_config import LIVE_BRIDGE_HOST as HOST, LIVE_BRIDGE_PORT as PORT  # noqa: E402

_persistent_ns = {"bpy": bpy}
_task_queue = queue.Queue()


def _reload_project_modules():
    """Framework source files change constantly during live development —
    without this, Python's module cache would keep serving whatever version
    of core/geometry/materials/etc. was on disk when Blender started,
    silently ignoring every subsequent edit until a restart."""
    for mod_name, mod in list(sys.modules.items()):
        mod_file = getattr(mod, "__file__", None)
        if mod_file and mod_file.startswith(PROJECT_ROOT):
            try:
                importlib.reload(mod)
            except Exception:
                pass  # a broken edit will surface normally when the snippet re-imports it


def _execute(code):
    out, err = io.StringIO(), io.StringIO()
    status = "OK"
    try:
        _reload_project_modules()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            exec(compile(code, "<live-bridge>", "exec"), _persistent_ns)
    except Exception:
        status = "ERROR"
        err.write(traceback.format_exc())
    return f"{status}\n--OUT--\n{out.getvalue()}--ERR--\n{err.getvalue()}--END--\n"


def _drain_queue():
    """Runs on Blender's main thread via bpy.app.timers. Must return a float
    (seconds until next call) to keep repeating, per the timers API."""
    try:
        while True:
            code, conn = _task_queue.get_nowait()
            try:
                response = _execute(code)
                conn.sendall(response.encode("utf-8"))
            except Exception:
                pass
            finally:
                conn.close()
    except queue.Empty:
        pass
    return 0.05


def _serve_forever(srv):
    while True:
        conn, _addr = srv.accept()
        chunks = []
        try:
            while True:
                data = conn.recv(65536)
                if not data:
                    break
                chunks.append(data)
        except OSError:
            pass
        code = b"".join(chunks).decode("utf-8")
        _task_queue.put((code, conn))


def start():
    if bpy.app.driver_namespace.get("_claude_live_bridge_started"):
        print("Claude live-bridge already running, skipping re-start.")
        return

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))  # do this on the main thread so failures raise here, not silently in a thread
    srv.listen(8)

    bpy.app.driver_namespace["_claude_live_bridge_started"] = True
    threading.Thread(target=_serve_forever, args=(srv,), daemon=True).start()
    bpy.app.timers.register(_drain_queue, persistent=True)
    print(f"Claude live-bridge listening on {HOST}:{PORT} (project root on sys.path: {PROJECT_ROOT})", flush=True)


start()
