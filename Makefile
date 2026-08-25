TEST_DATABASE_URL ?=

.PHONY: backend-test backend-integration-test frontend-test frontend-analyze boundary-check migration-check verify dev dev-user dev-smoke dev-setup deploy deploy-app deploy-control-plane apps-cosa-test agent-worker

dev:
	$(MAKE) services-docker-up
	@attempt=0; until curl -fsS http://127.0.0.1:4000/ >/dev/null 2>&1 || test $$attempt -ge 30; do attempt=$$((attempt + 1)); sleep 1; done
	@echo "✅ Javis Services Cluster is ready at http://localhost:4000 (Dashboard: http://localhost:9400)"

dev-smoke:
	@ts=$$(date +%s); \
	 curl -fsS -X POST http://127.0.0.1:4000/identity/register -H "Content-Type: application/json" -d "{\"email\": \"smoke-$$ts@javis.local\", \"name\": \"Smoke User\", \"password\": \"smokepassword123\", \"workspaceName\": \"Smoke WS\"}" >/dev/null
	@echo "✅ Services Cluster Smoke Test passed!"

agent-core-test:
	PYTHONPATH=$(CURDIR) $(CURDIR)/.venv/bin/pytest tests/agent_core packages/agent_testkit -q

apps-cosa-test:
	PYTHONPATH=$(CURDIR) $(CURDIR)/.venv/bin/pytest tests/apps/cosa -q

# COSA Agent Worker — poll durable scheduled tasks (thay asyncio.create_task
# trong apps/cosa/api/routes.py), acquire lease durable, thực thi kernel.
# Chạy nhiều instance song song an toàn (atomic claim + lease). Cần
# AGENT_CORE_DATABASE_URL + COSA_CONTROL_PLANE_URL (mặc định
# http://127.0.0.1:4001, khớp `services-dev-cosa`) trỏ services/cosa thật
# đang chạy — xem COSA_FINAL_INTEGRATION_AND_LEGACY_EXIT_PLAN_2026-08-25.md
# §29.6 Phase 4.
agent-worker:
	PYTHONPATH=$(CURDIR) $(CURDIR)/.venv/bin/python -m apps.cosa.worker.main

frontend-test:
	cd frontend && flutter test

frontend-analyze:
	cd frontend && flutter analyze

boundary-check:
	# packages/agent_core phải độc lập với services/*, apps/* (chỉ apps/cosa mới
	# được compose cả hai phía), và không canonical dir nào (packages/*, apps/*,
	# services/*) được import từ legacy/ hoặc agentos/ (agentos đã archive vào
	# legacy/agent_runtime_archive/, xem tests/apps/cosa/test_services_boundary_audit.py).
	PYTHONPATH=$(CURDIR) $(CURDIR)/.venv/bin/pytest tests/apps/cosa/test_services_boundary_audit.py -q
	! rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib

verify: boundary-check agent-core-test frontend-test frontend-analyze

# ─────────────────────────────────────────────────────────────
# DEPLOY (VPS / Production)
# Chạy trên VPS sau khi git pull:
#   make deploy-app             ← chỉ app (Alembic + restart)
#   make deploy-control-plane   ← chỉ init control plane schema
#   make deploy                 ← full (app + control plane)
# ─────────────────────────────────────────────────────────────

deploy-app:
	docker compose pull
	docker compose up --build -d
	@attempt=0; until curl -fsS http://127.0.0.1:8000/ready; do attempt=$$((attempt + 1)); test $$attempt -lt 30 || { echo "brain-api not ready"; exit 1; }; sleep 2; done
	@echo "\n✅ App deployed and healthy."

deploy-control-plane:
	docker compose --profile control-plane run --rm migrate-control-plane

deploy: deploy-app deploy-control-plane
	@echo "✅ Full deploy complete."

# ─────────────────────────────────────────────────────────────
# SERVICES CLUSTER (Encore.ts + Realtime Agent)
# ─────────────────────────────────────────────────────────────

# services/ được tách thành 2 Encore app độc lập (2026-08-23): `company`
# (local: identity/operations/commercial/finance-legal) và `cosa` (VPS:
# tenancy/license/agent-policy) — mỗi app có encore.app riêng.
services-test: services-test-company services-test-cosa

services-test-company:
	cd services/company && encore test

services-test-cosa:
	cd services/cosa && encore test

services-dev-company:
	cd services/company && encore run --port=4000

services-dev-cosa:
	cd services/cosa && encore run --port=4001

# Chạy trực tiếp bằng Node host (không qua Docker) — nhanh, không phụ thuộc
# pull image. Postgres đích vẫn là container docker-compose (company_db/cosa_db),
# chỉ có tiến trình chạy migration là chạy ngay trên host.
services-migrate-company:
	cd services/company && node scripts/migrate.mjs

services-migrate-cosa:
	cd services/cosa && node scripts/migrate.mjs

migrate-agent-platform:
	python -m packages.agent_core.scripts.migrate

services-docker-up:
	docker compose -f services/docker-compose.yml up --build -d

services-docker-down:
	docker compose -f services/docker-compose.yml down

services-docker-logs:
	docker compose -f services/docker-compose.yml logs -f

