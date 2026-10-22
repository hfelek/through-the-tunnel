.PHONY: dev test lint montecarlo summary

dev:
	@trap 'kill 0' INT TERM EXIT; \
	uvicorn sim.api.main:app --reload --port 8000 & \
	cd web && npm run dev & \
	wait

test:
	pytest -q

lint:
	ruff check -q

# Monte Carlo study (T9.1): make montecarlo ARGS="--seeds 50 --jobs 4"; side studies with ARGS="--study a30"
montecarlo:
	python -m sim.eval.montecarlo $(ARGS)

# tables and plots from the CSV files, without rerunning anything
summary:
	python -m sim.eval.summary $(ARGS)
