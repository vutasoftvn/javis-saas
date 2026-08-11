.PHONY: backend-test frontend-test frontend-analyze boundary-check migration-check verify

backend-test:
	PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/pytest backend/app/tests -q

frontend-test:
	cd frontend && flutter test

frontend-analyze:
	cd frontend && flutter analyze

boundary-check:
	! rg -n --glob '!build/**' '(:8888|backend/server|javis/|web_socket_channel)' frontend/lib
	! rg -n 'uuid\\.|uuid\\.UUID|PG_UUID|postgresql\\.UUID|sa\\.UUID' backend/app --glob '*.py'

migration-check:
	DATABASE_URL=postgresql://javis:javis@127.0.0.1:5432/javis PYTHONPATH=$(CURDIR)/backend $(CURDIR)/.venv/bin/alembic -c backend/alembic.ini check

verify: boundary-check backend-test frontend-test frontend-analyze
