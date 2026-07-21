.PHONY: help install dev qcluster test test-fast lint format migrate makemigrations shell superuser clean

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	uv venv --python 3.12
	uv pip install -r requirements/dev.txt
	bash scripts/install_vendor_assets.sh

dev: ## Run dev server (with seed)
	uv run python manage.py migrate
	uv run python manage.py seed_demo
	uv run python manage.py ensure_tt133_charts
	uv run uvicorn config.asgi:application --host 0.0.0.0 --port 8903 --reload

qcluster: ## Start django-q2 cluster
	uv run python manage.py qcluster

test: ## Run tests
	uv run pytest

test-fast: ## Run tests parallel
	uv run pytest -n auto

lint: ## Run linters
	uv run ruff check apps/
	uv run ruff format --check apps/

format: ## Format code
	uv run ruff format apps/

migrate: ## Run migrations
	uv run python manage.py migrate

makemigrations: ## Create migrations
	uv run python manage.py makemigrations

shell: ## Django shell
	uv run python manage.py shell

superuser: ## Create superuser
	uv run python manage.py createsuperuser

seed: ## Seed demo data
	uv run python manage.py seed_demo
	uv run python manage.py ensure_tt133_charts

clean: ## Clean caches
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
