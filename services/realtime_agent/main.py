import os

from dotenv import load_dotenv

# This is a standalone process (not a backend/app request handler), so it
# does not inherit backend/app/main.py's dotenv load - LIVEKIT_*/GOOGLE_API_KEY
# live in backend/.env as the single source of truth rather than being
# duplicated into a second secrets file here.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))

import httpx

def _resolve_local_livekit() -> None:
    # Check if local docker LiveKit is running on 7880
    try:
        with httpx.Client(timeout=0.5) as client:
            resp = client.get(os.environ.get("LIVEKIT_LOCAL_HTTP_URL", "http://127.0.0.1:7880"))
            local_healthy = resp.status_code < 500
    except Exception:
        local_healthy = False

    if local_healthy and os.environ.get("LIVEKIT_FORCE_CLOUD", "").lower() not in ("1", "true", "yes"):
        os.environ["LIVEKIT_URL"] = os.environ.get("LIVEKIT_LOCAL_URL", "ws://127.0.0.1:7880")
        os.environ["LIVEKIT_API_KEY"] = os.environ.get("LIVEKIT_LOCAL_API_KEY", "devkey")
        os.environ["LIVEKIT_API_SECRET"] = os.environ.get("LIVEKIT_LOCAL_API_SECRET", "secret_local_cosa_desktop_key")


_resolve_local_livekit()

from livekit.agents import WorkerOptions, cli  # noqa: E402 (needs env vars loaded first)

from agent import entrypoint, prewarm  # noqa: E402

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))

