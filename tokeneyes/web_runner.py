"""Launch the TokenEyes web UI."""

from __future__ import annotations

import os
import sys


def serve():
    import uvicorn

    host = os.environ.get("TOKENEYES_HOST", "0.0.0.0")
    port = int(os.environ.get("TOKENEYES_PORT", "8765"))

    print(f"\n  TOKENEYES web UI → http://localhost:{port}\n")
    uvicorn.run(
        "web.app:app",
        host=host,
        port=port,
        reload="--reload" in sys.argv,
        app_dir=str(__import__("pathlib").Path(__file__).parent.parent),
    )


if __name__ == "__main__":
    serve()
