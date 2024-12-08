.PHONY: install format lint test clean

install:
	pip install -e ".[dev]"
	pre-commit install

format:
	black src tests
	isort src tests
	autoflake --in-place --recursive --remove-all-unused-imports src tests
	autopep8 --in-place --recursive --aggressive src tests

lint:
	flake8 src tests
	mypy src tests
	black --check src tests
	isort --check-only src tests

test:
	pytest

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
