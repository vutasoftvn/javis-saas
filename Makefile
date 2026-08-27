TEST_DATABASE_URL ?=

.PHONY: backend-test backend-integration-test frontend-test frontend-analyze boundary-check migration-check verify dev dev-user dev-smoke dev-setup deploy deploy-app deploy-control-plane apps-cosa-test agent-worker dev-infra dev-migrate dev-preflight dev-stack dev-status db-bootstrap migrate-all deploy-preflight

dev:
	$(MAKE) services-docker-up
	@attempt=0; until curl -fsS http://127.0.0.1:4000/ >/dev/null 2>&1 || test $$attempt -ge 30; do attempt=$$((attempt + 1)); sleep 1; done
	@echo "✅ Javis Services Cluster is ready at http://localhost:4000 (Dashboard: http://localhost:9400)"

dev-smoke:
	@ts=$$(date +%s); \
	 curl -fsS -X POST http://127.0.0.1:4000/identity/register -H "Content-Type: application/json" -d "{\"email\": \"smoke-$$ts@javis.local\", \"name\": \"Smoke User\", \"password\": \"smokepassword123\", \"workspaceName\": \"Smoke WS\"}" >/dev/null
	@echo "✅ Services Cluster Smoke Test passed!"

AGENT_CORE_TEST_DATABASE_URL ?= postgresql+asyncpg://javis:javis@127.0.0.1:5432/javis
CONTROL_PLANE_TEST_DATABASE_URL ?= postgresql://javis:javis@127.0.0.1:5432/cosa_control_plane

agent-core-test:
	PYTHONPATH=$(CURDIR) AGENT_CORE_TEST_DATABASE_URL="$(AGENT_CORE_TEST_DATABASE_URL)" $(CURDIR)/.venv/bin/pytest tests/agent_core packages/agent_testkit -q

apps-cosa-test:
	PYTHONPATH=$(CURDIR) AGENT_CORE_TEST_DATABASE_URL="$(AGENT_CORE_TEST_DATABASE_URL)" CONTROL_PLANE_TEST_DATABASE_URL="$(CONTROL_PLANE_TEST_DATABASE_URL)" $(CURDIR)/.venv/bin/pytest tests/apps/cosa -q

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
	# được compose cả hai phía). legacy/ đã xoá hẳn 2026-08-25 (Sub-project D —
	# xem docs/architecture/LEGACY_BACKEND_CAPABILITY_AUDIT_2026-08-25.md); test
	# dưới đây vẫn giữ lại làm regression guard nếu ai đó lỡ tay thêm import
	# legacy/agentos mới, xem tests/apps/cosa/test_services_boundary_audit.py.
	PYTHONPATH=$(CURDIR) $(CURDIR)/.venv/bin/pytest tests/apps/cosa/test_services_boundary_audit.py -q
	! rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib

verify: boundary-check agent-core-test apps-cosa-test services-test frontend-test frontend-analyze

# ─────────────────────────────────────────────────────────────
# DEPLOY (VPS / Production)
# Chạy trên VPS sau khi git pull:
#   make db-bootstrap           ← tạo volume PostgreSQL mới với init scripts
#   make migrate-all            ← chạy migrations (Agent Core → COSA → Company)
#   make deploy-preflight       ← kiểm tra prerequisites trước deploy
#   make deploy-app             ← chỉ app (build + restart cosa-api/cosa-worker)
#   make deploy                 ← full (preflight → migrate-all → app)
# ─────────────────────────────────────────────────────────────

db-bootstrap: ## Initialize a fresh PostgreSQL volume with bootstrap scripts
	@echo "Initializing fresh PostgreSQL database..."
	@if docker volume inspect cosa_postgres_data >/dev/null 2>&1; then \
		if [ -n "$$(docker volume inspect cosa_postgres_data -f '{{.Mountpoint}}' | xargs ls -A 2>/dev/null)" ]; then \
			echo "❌ ERROR: PostgreSQL volume already exists and is not empty."; \
			echo "   Refusing to auto-initialize to prevent data loss."; \
			echo "   To bootstrap an existing database with missing schemas:"; \
			echo "     1. Verify the instance is healthy"; \
			echo "     2. Back up the volume"; \
			echo "     3. Run: make migrate-all"; \
			exit 1; \
		fi; \
	fi
	docker compose up -d postgres
	docker compose exec -T postgres pg_isready -U $(POSTGRES_USER:-javis) || { echo "PostgreSQL failed to initialize"; exit 1; }
	@echo "✅ PostgreSQL initialized with bootstrap scripts."

migrate-all: ## Run database migrations in order: Agent Core → COSA Control Plane → Company
	@echo "Running migrations (Agent Core → COSA Control Plane → Company)..."
	python -m packages.agent_core.scripts.migrate
	cd services/cosa && node scripts/migrate.mjs
	cd services/company && node scripts/migrate.mjs
	@echo "✓ All migrations completed"

deploy-preflight: ## Verify prerequisites before deployment (backup policy, connectivity, health)
	@echo "Running deployment preflight checks..."
	@echo "✓ Checking database connectivity..."
	@curl -fsS http://127.0.0.1:4000/healthz >/dev/null 2>&1 || { echo "⚠ Company Service not yet running (will start during deploy)"; }
	@curl -fsS http://127.0.0.1:4001/healthz >/dev/null 2>&1 || { echo "⚠ COSA Control Plane not yet running (will start during deploy)"; }
	@echo "✓ Preflight checks complete"

deploy-app:
	docker compose pull
	docker compose --profile cosa up --build -d
	@attempt=0; until curl -fsS http://127.0.0.1:8001/healthz; do attempt=$$((attempt + 1)); test $$attempt -lt 30 || { echo "cosa-api not ready"; exit 1; }; sleep 2; done
	@echo "\n✅ App deployed and healthy."

# Deploy is explicitly sequential (preflight → migrate-all → deploy-app) even under -j.
# Each step via $(MAKE) in the recipe body ensures order regardless of Make flags.
deploy:
	$(MAKE) deploy-preflight
	$(MAKE) migrate-all
	$(MAKE) deploy-app
	@echo "✅ Full deploy complete."

# legacy Alembic (migrate-control-plane) đã xoá cùng legacy/backend 2026-08-25
# — schema cosa_control_plane giờ migrate qua baseline_v1 (services/cosa/migrations/).
# Kept as deprecated alias for backward compatibility; use migrate-all instead.
deploy-control-plane: services-migrate-cosa

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

# ─────────────────────────────────────────────────────────────
# LOCAL DEVELOPMENT STACK (Task 3: Explicit Topology & Contract)
# ─────────────────────────────────────────────────────────────
# Canonical host-based development topology:
# - PostgreSQL, MinIO, LiveKit run in Docker (docker-compose.yml)
# - Company Encore, COSA Control Plane Encore, FastAPI, Worker run on host
# - All talk to Docker infra via consistent loopback/host URLs
# - Configuration is explicit (fail-fast on missing contract)

dev-infra: ## Start only Postgres, MinIO and LiveKit containers
	@echo "Starting infrastructure (PostgreSQL, MinIO, LiveKit)..."
	docker compose up -d postgres minio livekit
	@echo "✓ Infrastructure started"

dev-migrate: ## Run Agent Core, COSA and Company migrations in order
	@echo "Running migrations (Agent Core → COSA Control Plane → Company)..."
	python -m packages.agent_core.scripts.migrate
	cd services/cosa && node scripts/migrate.mjs
	cd services/company && node scripts/migrate.mjs
	@echo "✓ All migrations completed"

dev-preflight: ## Validate config, migrations and dependency health
	@echo "Running preflight checks..."
	bash scripts/check-dev-preflight.sh

dev-stack: dev-infra dev-migrate ## Launch Company, COSA, API and worker with signal-cleanup trap
	@echo "Starting dev stack services..."
	@trap 'echo "Shutting down services..."; kill -TERM $$(jobs -p) 2>/dev/null; wait' EXIT INT TERM; \
	cd $(CURDIR)/services/company && encore run --port=4000 &\
	COMPANY_PID=$$!; \
	cd $(CURDIR)/services/cosa && encore run --port=4001 &\
	COSA_PID=$$!; \
	PYTHONPATH=$(CURDIR) python -m apps.cosa.api.main &\
	API_PID=$$!; \
	PYTHONPATH=$(CURDIR) python -m apps.cosa.worker.main &\
	WORKER_PID=$$!; \
	echo "Services launched (PIDs: Company=$$COMPANY_PID COSA=$$COSA_PID API=$$API_PID Worker=$$WORKER_PID)"; \
	echo "Waiting for health endpoints (60s timeout)..."; \
	attempt=0; \
	while [ $$attempt -lt 60 ]; do \
		if curl -fsS http://127.0.0.1:4000/healthz >/dev/null 2>&1 && \
		   curl -fsS http://127.0.0.1:4001/healthz >/dev/null 2>&1 && \
		   curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then \
			echo "✓ All services healthy"; \
			break; \
		fi; \
		attempt=$$((attempt + 1)); \
		sleep 1; \
	done; \
	if [ $$attempt -ge 60 ]; then \
		echo "✗ Services did not become healthy within 60 seconds"; \
		exit 1; \
	fi; \
	wait

dev-status: ## Show dev stack status
	@echo "=== COSA Development Stack Status ==="
	@echo ""
	@if curl -fsS http://127.0.0.1:4000/healthz >/dev/null 2>&1; then \
		echo "✓ Company Service (http://127.0.0.1:4000)"; \
	else \
		echo "✗ Company Service (http://127.0.0.1:4000)"; \
	fi
	@if curl -fsS http://127.0.0.1:4001/healthz >/dev/null 2>&1; then \
		echo "✓ COSA Control Plane (http://127.0.0.1:4001)"; \
	else \
		echo "✗ COSA Control Plane (http://127.0.0.1:4001)"; \
	fi
	@if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then \
		echo "✓ COSA FastAPI (http://127.0.0.1:8000)"; \
	else \
		echo "✗ COSA FastAPI (http://127.0.0.1:8000)"; \
	fi
	@if pgrep -f "python -m apps.cosa.worker" >/dev/null 2>&1; then \
		echo "✓ COSA Worker (running)"; \
	else \
		echo "✗ COSA Worker (not running)"; \
	fi
	@echo ""
	@echo "Infrastructure (Docker):"
	@docker compose ps postgres minio livekit 2>/dev/null || echo "Docker not available"

services-docker-up:
	docker compose -f services/docker-compose.yml up --build -d

services-docker-down:
	docker compose -f services/docker-compose.yml down

services-docker-logs:
	docker compose -f services/docker-compose.yml logs -f

