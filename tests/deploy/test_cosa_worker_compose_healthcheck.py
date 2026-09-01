from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = ROOT / "deploy/central_vps/docker-compose.prod.yaml"

def worker_block() -> str:
    source = COMPOSE.read_text()
    return source.split("  cosa-worker:\n", 1)[1].split("\n  # --------------------------------------------------------------------------", 1)[0]

def test_cosa_worker_healthcheck_queries_loopback_ready_endpoint() -> None:
    block = worker_block()
    assert 'COSA_WORKER_HEALTH_HOST: "127.0.0.1"' in block
    assert 'COSA_WORKER_HEALTH_PORT: "8090"' in block
    assert "curl -fsS http://127.0.0.1:8090/ready" in block
    assert "pgrep -f" not in block
