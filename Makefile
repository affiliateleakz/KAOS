.PHONY: dev down test test-api test-collectors test-core web-build scan
dev:            ## one-command local stack (mongo + api + web)
	@test -f .env || cp .env.example .env
	docker compose up --build
down:
	docker compose down
test: test-api test-collectors test-core
test-api:
	cd apps/api && MONGO_URL=$${MONGO_URL:-mongodb://localhost:27017} DB_NAME=$${DB_NAME:-kaos_test} python -m pytest -q
test-collectors:
	cd services/collectors && python -m pytest -q
test-core:
	cd packages/kaos-core && python -m pytest -q
web-build:
	cd apps/web && npm ci && CI=false npm run build
scan:
	gitleaks dir . --redact --no-banner
