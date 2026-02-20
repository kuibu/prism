.PHONY: up down logs test demo

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f gateway_api

test:
	docker compose run --rm gateway_api pytest -q

demo:
	@echo "Iteration 1 demo: start stack and check health"
	docker compose up -d --build
	curl -sS http://localhost:8080/api/v1/health/live | python3 -m json.tool
	curl -sS http://localhost:8080/api/v1/health/ready | python3 -m json.tool
