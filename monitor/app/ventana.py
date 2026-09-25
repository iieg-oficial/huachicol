import sys
import urllib.request

from app.api import DEPLOY_TOKEN_HEADER
from app.config import _as_int, _as_secret

ACCIONES = ("start", "end")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ACCIONES:
        print("uso: python -m app.ventana start|end", file=sys.stderr)
        return 2
    token = _as_secret("MONITOR_DEPLOY_TOKEN")
    if not token:
        print("falta el secret monitor_deploy_token", file=sys.stderr)
        return 1
    puerto = _as_int("MONITOR_API_PORT", 8090)
    request = urllib.request.Request(
        f"http://127.0.0.1:{puerto}/api/deploy/{argv[1]}",
        method="POST",
        data=b"",
        headers={DEPLOY_TOKEN_HEADER: token},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        print(response.read().decode())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
