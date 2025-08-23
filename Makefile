.PHONY: help install test lint format clean migrate runserver shell coverage security performance

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

install-pre-commit: ## Install pre-commit hooks
	pre-commit install

test: ## Run all tests
	python manage.py test --verbosity=2

test-modular: ## Run modular system tests specifically
	python manage.py test tests.test_modular_system --verbosity=2

test-coverage: ## Run tests with coverage report
	coverage run --source='.' manage.py test
	coverage report
	coverage html

lint: ## Run all linting checks
	flake8 .
	black --check --diff .
	isort --check-only --diff .
	mypy core/ --ignore-missing-imports --no-strict-optional

format: ## Format code with black and isort
	black .
	isort .

security: ## Run security checks
	bandit -r . -f json -o bandit-report.json
	safety check --json --output safety-report.json

performance: ## Run performance tests
	python -m pytest tests/test_modular_system.py::TestModularSystemPerformance -v

clean: ## Clean up Python cache files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -delete
	find . -type d -name "htmlcov" -exec rm -rf {} +

migrate: ## Run database migrations
	python manage.py makemigrations
	python manage.py migrate

migrate-modules: ## Run modular architecture migration
	python manage.py migrate_to_modules

runserver: ## Start development server
	python manage.py runserver

shell: ## Start Django shell
	python manage.py shell

collectstatic: ## Collect static files
	python manage.py collectstatic --noinput

superuser: ## Create superuser
	python manage.py createsuperuser

check-all: lint test security ## Run all checks (lint, test, security)

ci: ## Run CI checks locally
	make lint
	make test
	make security
	make test-coverage

dev-setup: install install-pre-commit migrate ## Complete development setup