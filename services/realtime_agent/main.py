import os

from dotenv import load_dotenv

# This is a standalone process (not a backend/app request handler), so it
# does not inherit backend/app/main.py's dotenv load - LIVEKIT_*/GOOGLE_API_KEY
# live in backend/.env as the single source of truth rather than being
# duplicated into a second secrets file here.
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env"))

from livekit.agents import WorkerOptions, cli  # noqa: E402 (needs env vars loaded first)

from agent import entrypoint, prewarm  # noqa: E402

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
