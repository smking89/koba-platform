"""Stdlib-only TCP client for the live Blender bridge (live/blender_live_server.py).

Usage:
  python3 scripts/blender_client.py path/to/snippet.py
  python3 scripts/blender_client.py -c "print(1+1)"
  python3 scripts/blender_client.py --check          # just test connectivity

Exit code is 0 on OK, 1 on ERROR or connection failure.
"""
import argparse
import os
import socket
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.blender_config import LIVE_BRIDGE_HOST as HOST, LIVE_BRIDGE_PORT as PORT  # noqa: E402


def is_running(host=HOST, port=PORT, timeout=1.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def send(code, host=HOST, port=PORT, timeout=60.0):
    with socket.create_connection((host, port), timeout=timeout) as s:
        s.sendall(code.encode("utf-8"))
        s.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            data = s.recv(65536)
            if not data:
                break
            chunks.append(data)
    return b"".join(chunks).decode("utf-8")


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("script", nargs="?", help="path to a .py file to execute in the live session")
    group.add_argument("-c", "--code", help="inline Python source to execute")
    group.add_argument("--check", action="store_true", help="just check whether the bridge is reachable")
    args = parser.parse_args()

    if args.check:
        ok = is_running()
        print("UP" if ok else "DOWN")
        sys.exit(0 if ok else 1)

    if args.code:
        code = args.code
    elif args.script:
        with open(args.script, "r") as f:
            code = f.read()
    else:
        parser.error("provide a script path, -c, or --check")
        return

    if not is_running():
        print("Live Blender bridge is not reachable at 127.0.0.1:8765.", file=sys.stderr)
        print("Start it with: blender --python live/blender_live_server.py", file=sys.stderr)
        sys.exit(1)

    response = send(code)
    print(response)
    sys.exit(0 if response.startswith("OK") else 1)


if __name__ == "__main__":
    main()
