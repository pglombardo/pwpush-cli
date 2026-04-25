#* Variables
SHELL := /usr/bin/env bash
PYTHON := python

#* Docker variables
IMAGE := pwpush
VERSION := latest

#* Poetry
.PHONY: poetry-download
poetry-download:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | $(PYTHON) -

.PHONY: poetry-remove
poetry-remove:
	curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | $(PYTHON) - --uninstall

#* Installation
.PHONY: install
install:
	poetry lock -n && poetry export --without-hashes > requirements.txt
	poetry install -n
	-poetry run mypy --install-types --non-interactive ./

.PHONY: pre-commit-install
pre-commit-install:
	poetry run pre-commit install

#* Formatters
.PHONY: codestyle
codestyle:
	poetry run pyupgrade --exit-zero-even-if-changed --py310-plus **/*.py
	poetry run isort --settings-path pyproject.toml ./
	poetry run black --config pyproject.toml ./

.PHONY: formatting
formatting: codestyle

#* Linting
.PHONY: test
test:
	poetry run pytest

.PHONY: check-codestyle
check-codestyle:
	poetry run isort --diff --check-only --settings-path pyproject.toml ./
	poetry run black --diff --check --config pyproject.toml ./
	poetry run darglint --verbosity 2 pwpush tests

.PHONY: mypy
mypy:
	poetry run mypy --config-file pyproject.toml ./

.PHONY: check-safety
check-safety:
	poetry check
	@tmp_requirements="$$(mktemp)"; \
	poetry export --without-hashes --only main -f requirements.txt -o "$$tmp_requirements"; \
	poetry run pip-audit --progress-spinner off -r "$$tmp_requirements"; \
	rm -f "$$tmp_requirements"
	poetry run bandit -ll --recursive pwpush tests

.PHONY: lint
lint: test check-codestyle mypy check-safety

#* Docker
# Example: make docker VERSION=latest
# Example: make docker IMAGE=some_name VERSION=0.1.0
.PHONY: docker-build
docker-build:
	@echo Building docker $(IMAGE):$(VERSION) ...
	docker build \
		-t $(IMAGE):$(VERSION) . \
		-f ./docker/Dockerfile --no-cache

# Example: make clean_docker VERSION=latest
# Example: make clean_docker IMAGE=some_name VERSION=0.1.0
.PHONY: docker-remove
docker-remove:
	@echo Removing docker $(IMAGE):$(VERSION) ...
	docker rmi -f $(IMAGE):$(VERSION)

#* Cleaning
.PHONY: pycache-remove
pycache-remove:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf

.PHONY: build-remove
build-remove:
	rm -rf build/

.PHONY: clean-all
clean-all: pycache-remove build-remove docker-remove

#* Release automation
# Usage: make release bump=patch (or minor/major)
# This will: bump version, commit, tag, push, and publish
.PHONY: release
release:
	@if [ -z "$(bump)" ]; then \
		echo "Error: bump type required. Usage: make release bump=patch (or minor/major)"; \
		exit 1; \
	fi
	@if ! echo "$(bump)" | grep -qE '^(patch|minor|major)$$'; then \
		echo "Error: bump must be one of: patch, minor, major"; \
		exit 1; \
	fi
	@echo "Releasing $(bump) version..."
	poetry version $(bump)
	NEW_VERSION=$$(poetry version -s); \
	echo "New version: $$NEW_VERSION"; \
	git add pyproject.toml; \
	git commit -m "Bump version to $$NEW_VERSION"; \
	git tag -a "v$$NEW_VERSION" -m "Version $$NEW_VERSION"; \
	git push oss HEAD; \
	git push oss "v$$NEW_VERSION"; \
	echo "Waiting for release-drafter to create draft release..."; \
	for i in 1 2 3 4 5; do \
		sleep 3; \
		if gh release view "v$$NEW_VERSION" >/dev/null 2>&1; then \
			echo "Publishing GitHub release..."; \
			gh release edit "v$$NEW_VERSION" --draft=false; \
			break; \
		fi; \
		echo "Waiting... ($$i/5)"; \
	done
	poetry publish --build
	@echo "Release complete!"
