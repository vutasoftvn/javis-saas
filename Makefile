TEST_DATABASE_URL ?=

.PHONY: backend-test backend-integration-test frontend-test frontend-analyze boundary-check migration-check verify

backend-test:
	PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/pytest backend/app/tests -q

backend-integration-test:
	@test -n "$(TEST_DATABASE_URL)" || (echo "TEST_DATABASE_URL is required for integration tests"; exit 2)
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini upgrade head
	DATABASE_URL=$(TEST_DATABASE_URL) PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini check
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

verify: boundary-check backend-test frontend-test frontend-analyze
