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

backend-test:
	PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/pytest backend/tests -q

backend-integration-test:
	@test -n "$(TEST_DATABASE_URL)" || (echo "TEST_DATABASE_URL is required for integration tests"; exit 2)
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini upgrade head
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini check
	CONTROL_PLANE_DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic_control_plane.ini upgrade head
	CONTROL_PLANE_DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic_control_plane.ini check
	DATABASE_URL=$(TEST_DATABASE_URL) RUN_DB_INTEGRATION=1 PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/pytest backend/tests -q

frontend-test:
	cd frontend && flutter test

frontend-analyze:
	cd frontend && flutter analyze

boundary-check:
	bash backend/cosa_core/check_boundary.sh
	! rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib
	# NOTE: the pattern below used to be double-escaped ('uuid\\.'), which never
	# matches real source (it looks for a literal backslash character) and made
	# this check a silent no-op. Fixed to the single-escaped 'uuid\.' so it
	# actually catches new UUID usage (Quyết định 5: pure Snowflake ID project-wide).
	# The --glob excludes below are files where 'uuid' pre-dates this fix and
	# were not part of the Snowflake/UUID mismatch cleanup (2026-08-21) -
	# tracked as separate follow-up debt, not swept in here to avoid silently
	# breaking CI over unrelated pre-existing code.
	! rg -n 'uuid\.|PG_UUID|postgresql\.UUID|sa\.UUID' backend --glob '*.py' \
	    --glob '!backend/.venv/**' \
	    --glob '!backend/business/marketing/app_generator_service.py' \
	    --glob '!backend/business/marketing/public_intake_service.py' \
	    --glob '!backend/integrations/workflows/runtime/runner.py' \
	    --glob '!backend/platform_core/policy_funding/services/automation_service.py' \
	    --glob '!backend/tests/extensions/test_mcp_provider.py' \
	    --glob '!backend/tests/organization/test_portfolio_router.py' \
	    --glob '!backend/tests/unit/test_public_intake_and_marketing_app.py' \
	    --glob '!backend/worker_main.py' \
	    --glob '!backend/workforce/agents/capabilities/providers/claude_code_provider.py' \
	    --glob '!backend/workforce/agents/capabilities/providers/native_cosa_provider.py' \
	    --glob '!backend/workforce/agents/delegation/worker.py' \
	    --glob '!backend/workforce/agents/execution/adapters/mock.py' \
	    --glob '!backend/workforce/api/admin_api.py' \
	    --glob '!backend/workforce/chat/worker_prompt.py' \
	    --glob '!backend/workforce/dispatcher/context_builder.py' \
	    --glob '!backend/workforce/extensions/mcp_provider.py' \
	    --glob '!backend/workforce/identity/context.py' \
	    --glob '!backend/workforce/tools/invocation/contracts.py'

migration-check:
	@test -n "$(TEST_DATABASE_URL)" || (echo "TEST_DATABASE_URL is required for migration checks"; exit 2)
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini check
	CONTROL_PLANE_DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic_control_plane.ini check


verify: boundary-check backend-test frontend-test frontend-analyze

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

