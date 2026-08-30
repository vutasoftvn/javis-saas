from pathlib import Path


def test_all_delegation_consumers_require_the_secret() -> None:
    compose = Path("deploy/central_vps/docker-compose.prod.yaml").read_text()
    required_expression = (
        "${COSA_COMPANY_DELEGATION_SECRET:?COSA_COMPANY_DELEGATION_SECRET required}"
    )

    for service in ("services-company:", "cosa-api:", "cosa-worker:"):
        body = compose.split(f"\n  {service}", 1)[1].split(
            "\n  # --------------------------------------------------------------------------", 1
        )[0]
        assert required_expression in body


def test_edge_rate_limit_attested_in_production_environment() -> None:
    env_example = Path("deploy/central_vps/.env.prod.example").read_text()
    assert "EDGE_RATE_LIMIT_ATTESTED" in env_example


def test_restore_test_freshness_gate_in_deploy_preflight() -> None:
    preflight = Path("scripts/backup/check-backup-freshness.sh").read_text()
    assert "RESTORE_TEST_MAX_AGE_HOURS" in preflight


def test_least_privilege_container_contracts() -> None:
    dockerfile_api = Path("apps/cosa/Dockerfile.api").read_text()
    assert "USER app" in dockerfile_api

    dockerfile_worker = Path("apps/cosa/Dockerfile.worker").read_text()
    assert "USER app" in dockerfile_worker

    services_dockerfile = Path("services/Dockerfile").read_text()
    assert "npm ci" in services_dockerfile

    compose_prod = Path("deploy/central_vps/docker-compose.prod.yaml").read_text()
    assert "cap_drop" in compose_prod
    assert "security_opt" in compose_prod


