.PHONY: install format lint test test-cov test-watch test-html clean

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
