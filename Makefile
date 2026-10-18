.PHONY: dev test lint

dev:
	@trap 'kill 0' INT TERM EXIT; \
	uvicorn sim.api.main:app --reload --port 8000 & \
	cd web && npm run dev & \
	wait

test:
	pytest -q

lint:
	ruff check -q
