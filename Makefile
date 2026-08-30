# QUY ƯỚC: Mọi target Python phải thực thi qua $(PYTHON) hoặc $(PYTEST), không gọi python/pytest trần.
TEST_DATABASE_URL ?=

PYTHON ?= $(shell test -x $(CURDIR)/.venv/bin/python && echo $(CURDIR)/.venv/bin/python || echo python3)
PYTEST ?= $(PYTHON) -m pytest

.PHONY: backend-test backend-integration-test frontend-test frontend-analyze boundary-check migration-check migration-compat-check test-migration-rollback tenancy-check skillpacks-validate verify dev dev-user dev-smoke dev-setup deploy deploy-app deploy-app-prod deploy-control-plane apps-cosa-test knowledge-ingestion-test agent-worker dev-infra dev-migrate dev-preflight dev-stack dev-status db-bootstrap migrate-all deploy-preflight python-test-unit python-test-integration desktop-worker-test realtime-agent-test verify-local lint lint-fix typecheck-py e2e-test schema-fingerprint-check schema-fingerprint-write contracts-gen contracts-check route-inventory route-inventory-check company-usage-inventory contract-freeze-check ai-compliance-production-gate

# Task 10 (audit fix, 2026-08-30) — trước đây `tests/e2e/test_ai_compliance_company_http.py`
# dùng `httpx.MockTransport` tự viết giả lập response Company (fake snapshot
# client mà plan cấm, chỉ chuyển xuống 1 lớp sâu hơn). Giờ target này áp
# migration company thật + để `tests/e2e/conftest.py::real_company_service`
# tự khởi `encore run` thật trên 1 cổng test riêng — không còn mock nào ở
# đường Python E2E. Cùng convention mật khẩu dev mặc định với
# `tenancy-check` ở trên và `deploy/postgres/init/01-create-app-roles.sql`.
ai-compliance-production-gate:
	cd services/company && WORKSPACE_MIGRATOR_DATABASE_URL="$${WORKSPACE_MIGRATOR_DATABASE_URL:-postgresql://workspace_migrator:change-me-workspace-migrator@127.0.0.1:5432/workspace?sslmode=disable}" node scripts/migrate.mjs
	cd services/company && WORKSPACE_DATABASE_URL="$${WORKSPACE_DATABASE_URL:-postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/workspace?sslmode=disable}" pnpm vitest run finance-legal/tests/ai-compliance-*.test.ts
	WORKSPACE_DATABASE_URL="$${WORKSPACE_DATABASE_URL:-postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/workspace?sslmode=disable}" PYTHONPATH=$(CURDIR) $(PYTEST) tests/apps/cosa/compliance tests/e2e/test_ai_compliance_company_http.py -q
	cd frontend && flutter test test/modules/legal/ai_compliance_service_test.dart test/data/models/ai_compliance_models_test.dart


dev:
	$(MAKE) services-docker-up
	@attempt=0; until curl -fsS http://127.0.0.1:4000/ >/dev/null 2>&1 || test $$attempt -ge 30; do attempt=$$((attempt + 1)); sleep 1; done
	@echo "✅ Javis Services Cluster is ready at http://localhost:4000 (Dashboard: http://localhost:9400)"

dev-smoke:
	@ts=$$(date +%s); \
	 curl -fsS -X POST http://127.0.0.1:4000/identity/register -H "Content-Type: application/json" -d "{\"email\": \"smoke-$$ts@javis.local\", \"name\": \"Smoke User\", \"password\": \"smokepassword123\", \"workspaceName\": \"Smoke WS\"}" >/dev/null
	@echo "✅ Services Cluster Smoke Test passed!"

AGENT_TEST_DATABASE_URL ?=
COSA_TEST_DATABASE_URL ?=

lint:            ## ruff check + format check
	$(PYTHON) -m ruff check packages/agent apps/cosa packages/agent_integrations
	$(PYTHON) -m ruff format --check packages/agent apps/cosa packages/agent_integrations

lint-fix:        ## ruff check --fix + format
	$(PYTHON) -m ruff check --fix packages/agent apps/cosa packages/agent_integrations
	$(PYTHON) -m ruff format packages/agent apps/cosa packages/agent_integrations

typecheck-py:    ## mypy type check
	$(PYTHON) -m mypy

agent-test:
	PYTHONPATH=$(CURDIR) AGENT_TEST_DATABASE_URL="$(AGENT_TEST_DATABASE_URL)" $(PYTEST) --cov=packages/agent --cov-fail-under=80 tests/agent packages/agent_testkit -q

apps-cosa-test:
	PYTHONPATH=$(CURDIR) AGENT_TEST_DATABASE_URL="$(AGENT_TEST_DATABASE_URL)" COSA_TEST_DATABASE_URL="$(COSA_TEST_DATABASE_URL)" AGENT_DATABASE_URL="" COSA_DATABASE_URL="" DATABASE_URL="" $(PYTEST) --cov=apps/cosa --cov-fail-under=78 tests/apps/cosa -q


knowledge-ingestion-test:
	# Bộ test tập trung cho governed knowledge ingestion (Phase A): unit contracts,
	# hostile-file preflight, converter sandbox, normalization, handler vertical,
	# release-readiness gate và API contract. Toàn bộ in-memory, không cần DB.
	PYTHONPATH=$(CURDIR) $(PYTEST) tests/apps/cosa/knowledge_ingestion tests/agent/knowledge/test_document_candidate.py -q

# COSA Agent Worker — poll durable scheduled tasks (thay asyncio.create_task
# trong apps/cosa/api/routes.py), acquire lease durable, thực thi kernel.
# Chạy nhiều instance song song an toàn (atomic claim + lease). Cần
# AGENT_DATABASE_URL + COSA_EXECUTION_PLANE_URL (local scheduler/lease,
# mặc định http://127.0.0.1:4001) và COSA_PLATFORM_CONTROL_PLANE_URL (VPS
# identity/connector/policy). Biến COSA_CONTROL_PLANE_URL cũ chỉ còn fallback.
# Xem SPEC-EXEC-PLANE-SPLIT + COSA_FINAL_INTEGRATION_..._2026-08-25.md §29.6.
agent-worker:
	PYTHONPATH=$(CURDIR) $(PYTHON) -m apps.cosa.worker.main

frontend-test:
	cd frontend && flutter test

frontend-analyze:
	cd frontend && flutter analyze

boundary-check:
	# packages/agent phải độc lập với services/*, apps/* (chỉ apps/cosa mới
	# được compose cả hai phía). legacy/ đã xoá hẳn 2026-08-25 (Sub-project D —
	# xem docs/architecture/LEGACY_BACKEND_CAPABILITY_AUDIT_2026-08-25.md); test
	# dưới đây vẫn giữ lại làm regression guard nếu ai đó lỡ tay thêm import
	# legacy/agentos mới, xem tests/apps/cosa/test_services_boundary_audit.py.
	PYTHONPATH=$(CURDIR) $(PYTEST) tests/apps/cosa/test_services_boundary_audit.py -q
	! rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib

skillpacks-validate:
	# Kiểm tra contract của tất cả skillpacks: manifest.yaml, SKILL.md frontmatter,
	# định danh công cụ, path nguồn, entrypoint — trước khi chạy integration tests.
	PYTHONPATH=$(CURDIR) $(PYTHON) scripts/validate_skillpacks.py


tenancy-check:
	# Workspace-only tenancy isolation gate: verify no product-side company_id leaks,
	# and that all tenant scoping works via X-Workspace-Id header.
	cd services/company && WORKSPACE_DATABASE_URL="$${WORKSPACE_DATABASE_URL:-postgresql://workspace_app:change-me-workspace-app@127.0.0.1:5432/workspace?sslmode=disable}" npx vitest run
	PYTHONPATH=$(CURDIR) $(PYTEST) tests/agent tests/apps/cosa/test_tenant_isolation.py -q
	cd frontend && flutter test test/auth_flow_test.dart test/modules/chat/chat_module_test.dart test/modules/chat/session_view_test.dart

python-test-unit:
	PYTHONPATH=$(CURDIR) $(PYTEST) --cov=packages/agent --cov-fail-under=80 tests/agent packages/agent_testkit -m "not integration" -q

python-test-integration:
	PYTHONPATH=$(CURDIR) AGENT_TEST_DATABASE_URL="$(AGENT_TEST_DATABASE_URL)" COSA_TEST_DATABASE_URL="$(COSA_TEST_DATABASE_URL)" $(PYTEST) tests/apps/cosa -m "integration and not live_provider" -q

desktop-worker-test:
	PYTHONPATH=$(CURDIR) $(PYTEST) tests/desktop_worker -q

realtime-agent-test:
	cd services/realtime_agent && PYTHONPATH=. $(PYTEST) tests -q

check-docs:
	bash scripts/check-doc-links.sh

# ─── Workspace-canonical contract freeze (M0) ───────────────────
contracts-gen:            ## Sinh mã enum canonical cho 3 runtime từ shared/contracts/enums.json
	node scripts/gen-contracts.mjs

contracts-check:          ## CI: fail nếu mã enum generated lệch nguồn
	node scripts/gen-contracts.mjs --check

route-inventory:          ## Sinh route-inventory.md + snapshot drift lint
	$(PYTHON) scripts/route_inventory.py

route-inventory-check:    ## CI: fail nếu route drift chưa khai báo trong snapshot/allowlist
	$(PYTHON) scripts/route_inventory.py --check

company-usage-inventory:  ## Sinh company-usage-inventory.md
	$(PYTHON) scripts/company_usage_inventory.py

contract-freeze-check: contracts-check route-inventory-check ## M0 gate tổng hợp
	$(PYTHON) scripts/route_inventory.py --check
	$(PYTHON) scripts/company_usage_inventory.py --check

e2e-test:        ## Run full-stack E2E golden path test suite
	PYTHONPATH=$(CURDIR) $(PYTEST) tests/e2e -q

verify-local: lint typecheck-py python-test-unit python-test-integration desktop-worker-test knowledge-ingestion-test boundary-check check-docs contract-freeze-check e2e-test

verify: lint typecheck-py boundary-check skillpacks-validate tenancy-check contract-freeze-check agent-test apps-cosa-test services-test frontend-test frontend-analyze check-docs


# ─────────────────────────────────────────────────────────────
# DEPLOY (VPS / Production)
# Chạy trên VPS sau khi git pull:
#   make db-bootstrap           ← tạo volume PostgreSQL mới với init scripts
#   make migrate-all            ← chạy migrations (Agent Core → COSA → Company)
#   make deploy-preflight       ← kiểm tra prerequisites trước deploy
#   make deploy-app             ← chỉ app (build + restart cosa-api/cosa-worker)
#   make deploy-app-prod        ← prod-path qua docker-compose.prod.yaml (migrate one-shot + 4 unit)
#   make deploy                 ← full (preflight → migrate-all → app)
# ─────────────────────────────────────────────────────────────

db-bootstrap: ## Initialize a fresh PostgreSQL volume with bootstrap scripts
	@echo "Initializing fresh PostgreSQL database..."
	@# Verify bootstrap scripts exist before attempting initialization
	@test -d deploy/postgres/init || { echo "❌ ERROR: deploy/postgres/init directory not found"; echo "   Cannot initialize database without bootstrap scripts"; exit 1; }
	@test -f deploy/postgres/init/01-create-app-roles.sql || { echo "❌ ERROR: deploy/postgres/init/01-create-app-roles.sql not found"; echo "   Bootstrap SQL scripts are required"; exit 1; }
	@echo "✓ Bootstrap scripts present"
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
	docker compose exec -T postgres pg_isready -U $(POSTGRES_USER:-postgres) -d $(POSTGRES_DB:-postgres) || { echo "PostgreSQL failed to initialize"; exit 1; }
	@echo "✅ PostgreSQL initialized with bootstrap scripts."

migrate-all: ## Run database migrations in order: Agent Core → COSA Control Plane → Company
	@echo "Running migrations (Agent Core → COSA Control Plane → Company)..."
	$(PYTHON) -m packages.agent.scripts.migrate
	cd services/cosa && node scripts/migrate.mjs
	cd services/company && node scripts/migrate.mjs
	@echo "✓ All migrations completed"

schema-fingerprint-check: ## So schema thực với golden
	node scripts/schema-fingerprint.mjs --check

schema-fingerprint-write: ## Cập nhật golden schema fingerprint
	node scripts/schema-fingerprint.mjs --write

migration-compat-check: ## Kiểm tra Expand-Contract backward compatibility cho migrations
	node scripts/check-migration-backward-compat.mjs

test-migration-rollback: ## Test migration rollback round-trip (Migration Gate E)
	node scripts/test-migration-rollback.mjs

migration-check: migration-compat-check schema-fingerprint-check ## Full migration quality gate (compat check + fingerprint)

deploy-preflight: ## Verify prerequisites before deployment (backup policy, connectivity, health)
	@echo "Running deployment preflight checks..."
	@# Check required environment variables for deployment
	@test -n "$$AGENT_DATABASE_URL" || { echo "❌ AGENT_DATABASE_URL is required"; exit 1; }
	@test -n "$$COSA_DATABASE_URL" || { echo "❌ COSA_DATABASE_URL is required"; exit 1; }
	@test -n "$$WORKSPACE_DATABASE_URL" || { echo "❌ WORKSPACE_DATABASE_URL is required"; exit 1; }
	@test -n "$$AGENT_MIGRATOR_DATABASE_URL" || { echo "❌ AGENT_MIGRATOR_DATABASE_URL is required"; exit 1; }
	@test -n "$$COSA_MIGRATOR_DATABASE_URL" || { echo "❌ COSA_MIGRATOR_DATABASE_URL is required"; exit 1; }
	@test -n "$$WORKSPACE_MIGRATOR_DATABASE_URL" || { echo "❌ WORKSPACE_MIGRATOR_DATABASE_URL is required"; exit 1; }
	@test -n "$$PLATFORM_JWT_SECRET" || { echo "❌ PLATFORM_JWT_SECRET is required"; exit 1; }
	@test -n "$$WORKER_SERVICE_JWT_SECRET" || { echo "❌ WORKER_SERVICE_JWT_SECRET is required"; exit 1; }
	@test -n "$$COSA_WORKER_SERVICE_TOKEN" || { echo "❌ COSA_WORKER_SERVICE_TOKEN is required"; exit 1; }
	@test -n "$$DEEPSEEK_API_KEY" || { echo "❌ DEEPSEEK_API_KEY is required"; exit 1; }
	@echo "✓ All required environment variables present"
	@# Verify database connectivity (migration scripts will verify full connectivity during migrate-all)
	@echo "✓ Database URLs configured"
	@# Verify Company and COSA Control Plane services are healthy (hard fail if not running)
	@echo "Checking service health..."
	@curl -fsS http://127.0.0.1:4000/healthz >/dev/null 2>&1 || { echo "❌ Company Service not reachable at http://127.0.0.1:4000"; exit 1; }
	@curl -fsS http://127.0.0.1:4001/healthz >/dev/null 2>&1 || { echo "❌ COSA Control Plane not reachable at http://127.0.0.1:4001"; exit 1; }
	@echo "✓ All services healthy"
	@# Backup policy (Part 2E.1): kiểm backup gần nhất < 24h + restore-test < 30 ngày
	@# qua manifest thật. DEPLOY_BACKUP_CONFIRMED=true vẫn override được (có lý do).
	@echo "Checking backup policy (freshness + restore-test recency)..."
	@bash scripts/backup/check-backup-freshness.sh
	@# Verify migration checksums (all three systems: Agent Core, COSA, Company) — hard fail if drift detected
	@echo "Checking migration checksum state..."
	@$(PYTHON) -m packages.agent.scripts.migrate --check || { echo "❌ Agent Core migration checksum verification failed"; exit 1; }
	@(cd services/cosa && node scripts/migrate.mjs --check) || { echo "❌ COSA migration checksum verification failed"; exit 1; }
	@(cd services/company && node scripts/migrate.mjs --check) || { echo "❌ Company migration checksum verification failed"; exit 1; }
	@echo "✓ Migration checksums valid (no drift detected)"
	@echo "✓ All preflight checks passed"

deploy-app:
	docker compose pull
	docker compose --profile cosa up --build -d
	@attempt=0; until curl -fsS http://127.0.0.1:8001/healthz; do attempt=$$((attempt + 1)); test $$attempt -lt 30 || { echo "cosa-api not ready"; exit 1; }; sleep 2; done
	@echo "\n✅ App deployed and healthy."

# Prod-path deploy qua deploy/central_vps/docker-compose.prod.yaml (ADR-DEPLOY-001).
# migrate one-shot chạy trước (Migration Gate G); app chờ service_completed_successfully.
# COMPOSE_PROD_ENV mặc định .env.prod trong thư mục đó.
COMPOSE_PROD ?= deploy/central_vps/docker-compose.prod.yaml
COMPOSE_PROD_ENV ?= deploy/central_vps/.env.prod
deploy-app-prod:
	docker compose -f $(COMPOSE_PROD) --env-file $(COMPOSE_PROD_ENV) config --quiet
	docker compose -f $(COMPOSE_PROD) --env-file $(COMPOSE_PROD_ENV) run --rm migrate
	docker compose -f $(COMPOSE_PROD) --env-file $(COMPOSE_PROD_ENV) up --build -d
	@attempt=0; until curl -fsS http://127.0.0.1:8000/healthz; do attempt=$$((attempt + 1)); test $$attempt -lt 45 || { echo "cosa-api not ready"; exit 1; }; sleep 2; done
	@echo "\n✅ Prod stack deployed and healthy."

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
	$(PYTHON) -m packages.agent.scripts.migrate

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
	$(PYTHON) -m packages.agent.scripts.migrate
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
	PYTHONPATH=$(CURDIR) $(PYTHON) -m apps.cosa.api.main &\
	API_PID=$$!; \
	PYTHONPATH=$(CURDIR) $(PYTHON) -m apps.cosa.worker.main &\
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

ai-compliance-test:
	cd services/company && npx vitest run finance-legal/tests/ai-*.test.ts
	PYTHONPATH=$(CURDIR) $(PYTEST) tests/apps/cosa/compliance -q
	cd frontend && flutter test test/modules/legal/compliance_center_test.dart test/modules/legal/contract_risk_analyzer_dialog_test.dart test/modules/chat/ai_advisory_disclosure_test.dart

ai-compliance-smoke:
	PYTHONPATH=$(CURDIR) $(PYTEST) tests/apps/cosa/compliance/test_process_smoke.py tests/e2e/test_ai_compliance_flow.py -q
