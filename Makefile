TEST_DATABASE_URL ?=

.PHONY: backend-test backend-integration-test frontend-test frontend-analyze boundary-check migration-check verify dev dev-user dev-smoke dev-setup deploy deploy-app deploy-control-plane

dev:
	$(MAKE) services-docker-up
	@attempt=0; until curl -fsS http://127.0.0.1:4000/ >/dev/null 2>&1 || test $$attempt -ge 30; do attempt=$$((attempt + 1)); sleep 1; done
	@echo "✅ Javis Services Cluster is ready at http://localhost:4000 (Dashboard: http://localhost:9400)"

dev-smoke:
	@ts=$$(date +%s); \
	 curl -fsS -X POST http://127.0.0.1:4000/identity/register -H "Content-Type: application/json" -d "{\"email\": \"smoke-$$ts@javis.local\", \"name\": \"Smoke User\", \"password\": \"smokepassword123\", \"workspaceName\": \"Smoke WS\"}" >/dev/null
	@echo "✅ Services Cluster Smoke Test passed!"

agentos-test:
	PYTHONPATH=$(CURDIR) $(CURDIR)/.venv/bin/pytest tests/agentos -q

frontend-test:
	cd frontend && flutter test

frontend-analyze:
	cd frontend && flutter analyze

boundary-check:
	# agentos/core is the Agent Core kernel — it must never import from the
	# business-domain-facing tool clusters (agentos/tools/clusters/*), only
	# the other way around. Legacy backend/cosa_core/check_boundary.sh was
	# removed with backend/ (moved to legacy/, 2026-08-22).
	! rg -n 'from agentos\.tools\.clusters|import agentos\.tools\.clusters' agentos/core --glob '*.py'
	! rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib

verify: boundary-check agentos-test frontend-test frontend-analyze

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

services-test:
	cd services && encore test

services-dev:
	cd services && encore run

services-docker-up:
	docker compose -f services/docker-compose.yml up --build -d

services-docker-down:
	docker compose -f services/docker-compose.yml down

services-docker-logs:
	docker compose -f services/docker-compose.yml logs -f

