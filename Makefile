.PHONY: install format lint test test-cov test-watch test-html clean e2e-build e2e-up e2e-down e2e-logs e2e-clean

install:
	pip install -e ".[dev]"
	pre-commit install

format:
	black src tests --exclude "docs/"
	isort src tests --skip docs/
	autoflake --in-place --recursive --remove-all-unused-imports --exclude docs/ src tests
	autopep8 --in-place --recursive --aggressive --exclude "docs/*" src tests

lint:
	flake8 src tests --exclude docs/
	mypy src tests --exclude docs/
	black --check src tests --exclude "docs/"
	isort --check-only src tests --skip docs/

test:
	pytest -v

test-cov:
	pytest --cov=mailos tests/ --cov-report=term-missing

test-watch:
	pytest-watch -- -v

test-html:
	pytest --cov=mailos tests/ --cov-report=html

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# E2E Testing Commands
e2e-up:
	docker-compose -f e2e/docker-compose.yml up --build -d

e2e-down:
	docker-compose -f e2e/docker-compose.yml down

e2e-logs:
	docker-compose -f e2e/docker-compose.yml logs -f

e2e-clean: e2e-down
	docker-compose -f e2e/docker-compose.yml down -v --remove-orphans
	docker system prune -f --filter "label=com.docker.compose.project=e2e"
