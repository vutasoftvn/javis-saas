TEST_DATABASE_URL ?=

.PHONY: backend-test backend-integration-test frontend-test frontend-analyze boundary-check migration-check verify dev dev-user dev-smoke dev-setup deploy deploy-app deploy-control-plane

dev:
	docker compose up --build -d
	@attempt=0; until curl -fsS http://127.0.0.1:8000/ready; do attempt=$$((attempt + 1)); test $$attempt -lt 30 || { echo "brain-api did not become ready"; exit 1; }; sleep 1; done

dev-user:
	@test -n "$(DEV_ADMIN_PASSWORD)" || (echo "DEV_ADMIN_PASSWORD is required"; exit 2)
	docker compose exec -T -e DEV_ADMIN_PASSWORD brain-api python -m app.scripts.bootstrap_dev_user

dev-smoke:
	@test -n "$(DEV_ADMIN_PASSWORD)" || (echo "DEV_ADMIN_PASSWORD is required"; exit 2)
	@curl -fsS http://127.0.0.1:8000/ready >/dev/null
	@token=$$(curl -fsS -X POST http://127.0.0.1:8000/api/v1/auth/sessions -H 'Content-Type: application/x-www-form-urlencoded' --data-urlencode 'username=admin@javis.local' --data-urlencode "password=$$DEV_ADMIN_PASSWORD" | python3 -c 'import json, sys; print(json.load(sys.stdin)["access_token"])'); \
	 curl -fsS http://127.0.0.1:8000/api/v1/auth/me -H "Authorization: Bearer $$token" | python3 -c 'import json, sys; identity = json.load(sys.stdin); assert identity["email"] == "admin@javis.local"; assert identity["workspace_id"] and identity["brain_id"]; print("Development smoke passed")'

dev-setup:
	@test -n "$(DEV_ADMIN_PASSWORD)" || (echo "DEV_ADMIN_PASSWORD is required"; exit 2)
	$(MAKE) dev
	$(MAKE) dev-user
	$(MAKE) dev-smoke

backend-test:
	PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/pytest backend/app/tests -q

backend-integration-test:
	@test -n "$(TEST_DATABASE_URL)" || (echo "TEST_DATABASE_URL is required for integration tests"; exit 2)
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini upgrade head
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini check
	CONTROL_PLANE_DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic_control_plane.ini upgrade head
	CONTROL_PLANE_DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic_control_plane.ini check
	DATABASE_URL=$(TEST_DATABASE_URL) RUN_DB_INTEGRATION=1 PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/pytest backend/app/tests -q

frontend-test:
	cd frontend && flutter test

frontend-analyze:
	cd frontend && flutter analyze

boundary-check:
	! rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib
	! rg -n 'uuid\\.|uuid\\.UUID|PG_UUID|postgresql\\.UUID|sa\\.UUID' backend/app --glob '*.py'

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
