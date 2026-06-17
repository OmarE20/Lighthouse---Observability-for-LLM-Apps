.PHONY: install serve dashboard example test docker overhead

install:
	pip install -e ".[dev,server,openai,anthropic]"
	cd dashboard && npm install

serve:
	uvicorn server.main:app --reload --port 8000

dashboard:
	cd dashboard && npm run dev

example:
	python examples/run_example.py

overhead:
	python examples/measure_overhead.py

test:
	pytest -q

docker:
	docker compose up --build
