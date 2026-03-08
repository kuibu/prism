.PHONY: up down logs test live-test demo mac-client-install mac-client-dev mac-client-check mac-client-dist mac-client-dist-dir mac-client-publish mac-release-run

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f gateway_api

test:
	docker compose run --rm gateway_api pytest -q

live-test:
	PRISM_RUN_LIVE_TESTS=1 .venv/bin/pytest -q services/gateway_api/app/tests/test_live_integration.py

demo:
	@echo "Prism end-to-end demo: start stack, verify health, run grant/revoke/audit flow"
	docker compose up -d --build
	@for i in $$(seq 1 40); do \
		if curl -fsS http://localhost:8080/api/v1/health/live >/dev/null 2>&1; then \
			break; \
		fi; \
		sleep 1; \
	done
	curl -sS http://localhost:8080/api/v1/health/live | python3 -m json.tool
	curl -sS http://localhost:8080/api/v1/health/ready | python3 -m json.tool
	python3 scripts/demo_flow.py

mac-client-install:
	cd clients/mac && npm install

mac-client-dev:
	cd clients/mac && PRISM_WEB_URL=http://localhost:8080/web/ npm run dev

mac-client-check:
	cd clients/mac && npm run check

mac-client-dist:
	cd clients/mac && npm run dist:mac

mac-client-dist-dir:
	cd clients/mac && npm run dist:mac:dir

mac-client-publish:
	cd clients/mac && npm run dist:mac:publish

mac-release-run:
	@if [ -z "$(VERSION)" ]; then \
		echo "Usage: make mac-release-run VERSION=0.1.1"; \
		exit 1; \
	fi
	gh workflow run mac-release.yml --repo kuibu/prism -f version=$(VERSION)
