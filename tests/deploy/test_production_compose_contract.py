from pathlib import Path


def test_all_delegation_consumers_require_the_secret() -> None:
    compose = Path("deploy/central_vps/docker-compose.prod.yaml").read_text()

    for service in ("services-company:", "cosa-api:", "cosa-worker:"):
        body = compose.split(f"\n  {service}", 1)[1].split(
            "\n  # --------------------------------------------------------------------------", 1
        )[0]
        assert "COSA_COMPANY_DELEGATION_SECRET" in body
