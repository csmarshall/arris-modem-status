# Makefile for arris-modem-status
# Streamlined version with essential commands only
# Author: Charles Marshall

.PHONY: help setup-dev dev-check test clean build release
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Project variables
PYTHON := python3
PIP := pip3
PROJECT_NAME := arris-modem-status

help: ## Show available commands
	@echo "$(BLUE)🚀 arris-modem-status Development Commands$(RESET)"
	@echo ""
	@echo "$(YELLOW)Essential Commands:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | while read -r line; do \
		target=$$(echo "$$line" | cut -d':' -f1); \
		desc=$$(echo "$$line" | sed 's/^[^:]*:.*## //'); \
		printf "$(BLUE)%-20s$(RESET) %s\n" "$$target" "$$desc"; \
	done
	@echo ""
	@echo "$(YELLOW)Quick Start:$(RESET)"
	@echo "  $(BLUE)make setup-dev$(RESET)     # One-time development setup"
	@echo "  $(BLUE)make dev-check$(RESET)     # Validate code before commit"
	@echo "  $(BLUE)make release$(RESET)       # Release to PyPI (after version bump)"

## Development Environment
setup-dev: ## Setup complete development environment
	@echo "$(GREEN)🔧 Setting up development environment...$(RESET)"
	$(PIP) install --upgrade pip wheel
	$(PIP) install -e .[dev,test,build]
	pre-commit install --hook-type pre-commit --hook-type pre-push
	@echo "$(GREEN)✅ Development environment ready!$(RESET)"
	@echo "$(BLUE)💡 Next: Run 'make dev-check' to validate setup$(RESET)"

## Code Quality & Testing
dev-check: ## Complete development validation (format, lint, type-check, test)
	@echo "$(GREEN)🔍 Running complete development validation...$(RESET)"
	@echo "$(BLUE)Step 1/4: Code formatting$(RESET)"
	black arris_modem_status tests --line-length 120
	ruff check --fix arris_modem_status tests
	@echo "$(BLUE)Step 2/4: Linting$(RESET)"
	ruff check arris_modem_status tests
	@echo "$(BLUE)Step 3/4: Type checking$(RESET)"
	mypy arris_modem_status --ignore-missing-imports
	@echo "$(BLUE)Step 4/4: Running tests$(RESET)"
	pytest tests/ -v --cov=arris_modem_status --cov-report=term-missing
	@echo "$(GREEN)✅ All development checks passed - ready to commit!$(RESET)"

test: ## Run all tests with coverage
	@echo "$(GREEN)🧪 Running full test suite...$(RESET)"
	pytest tests/ -v --cov=arris_modem_status --cov-report=term-missing --cov-report=html
	@echo "$(GREEN)✅ Tests complete (coverage report: htmlcov/index.html)$(RESET)"

test-quick: ## Quick test without coverage
	@echo "$(GREEN)⚡ Running quick tests...$(RESET)"
	pytest tests/ -x -q -m "not integration"
	@echo "$(GREEN)✅ Quick tests complete$(RESET)"

format: ## Format code with Black and Ruff
	@echo "$(GREEN)🎨 Formatting code...$(RESET)"
	black arris_modem_status tests --line-length 120
	ruff check --fix arris_modem_status tests
	@echo "$(GREEN)✅ Code formatting complete$(RESET)"

lint: ## Run linting checks
	@echo "$(GREEN)🔍 Running linting checks...$(RESET)"
	ruff check arris_modem_status tests
	@echo "$(GREEN)✅ Linting complete$(RESET)"

typecheck: ## Run type checking
	@echo "$(GREEN)🔍 Running type checking...$(RESET)"
	mypy arris_modem_status --ignore-missing-imports
	@echo "$(GREEN)✅ Type checking complete$(RESET)"

security: ## Run security checks
	@echo "$(GREEN)🔒 Running security checks...$(RESET)"
	bandit -r arris_modem_status -ll
	pip-audit --desc --skip-editable --ignore-vuln PYSEC-2022-42969
	@echo "$(GREEN)✅ Security checks complete$(RESET)"

## Build & Release
clean: ## Clean build artifacts and cache files
	@echo "$(GREEN)🧹 Cleaning build artifacts...$(RESET)"
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ .mypy_cache/ .coverage htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "$(GREEN)✅ Cleanup complete$(RESET)"

build: clean ## Build distribution packages
	@echo "$(GREEN)📦 Building distribution packages...$(RESET)"
	$(PYTHON) -m build
	$(PYTHON) -m twine check dist/*
	@echo "$(GREEN)✅ Build complete - packages ready in dist/$(RESET)"

build-check: ## Validate build artifacts
	@echo "$(GREEN)🔍 Checking build artifacts...$(RESET)"
	$(PYTHON) -m twine check dist/*
	@echo "$(GREEN)✅ Build artifacts valid$(RESET)"

package-contents: ## Show what files will be included in PyPI package
	@echo "$(GREEN)📦 Checking package contents...$(RESET)"
	@if [ -f "scripts/verify_package_contents.py" ]; then \
		$(PYTHON) scripts/verify_package_contents.py; \
	else \
		echo "$(YELLOW)Building temporary package to check contents...$(RESET)"; \
		$(PYTHON) -m build --wheel --outdir temp_check; \
		unzip -l temp_check/*.whl | grep -E "(scripts/|debug_tools/|tests/)" && echo "$(RED)❌ Found excluded files in package!$(RESET)" || echo "$(GREEN)✅ No excluded files found$(RESET)"; \
		rm -rf temp_check; \
	fi

## Version Management
version: ## Show current version
	@echo "$(BLUE)Current version:$(RESET)"
	@grep -E '^__version__' arris_modem_status/__init__.py | cut -d'"' -f2

version-patch: ## Bump patch version (1.0.0 → 1.0.1)
	@echo "$(GREEN)📈 Bumping patch version...$(RESET)"
	bump-my-version bump patch
	@echo "$(GREEN)✅ Patch version bumped to $$(make version)$(RESET)"

version-minor: ## Bump minor version (1.0.0 → 1.1.0)
	@echo "$(GREEN)📈 Bumping minor version...$(RESET)"
	bump-my-version bump minor
	@echo "$(GREEN)✅ Minor version bumped to $$(make version)$(RESET)"

version-major: ## Bump major version (1.0.0 → 2.0.0)
	@echo "$(YELLOW)📈 Bumping major version (breaking changes)...$(RESET)"
	@read -p "Are you sure? This indicates breaking changes (y/N): " confirm && [ "$$confirm" = "y" ]
	bump-my-version bump major
	@echo "$(GREEN)✅ Major version bumped to $$(make version)$(RESET)"

## Release to PyPI
release-test: build ## Test release to TestPyPI
	@echo "$(YELLOW)🧪 Uploading to TestPyPI...$(RESET)"
	$(PYTHON) -m twine upload --repository testpypi dist/*
	@echo "$(GREEN)✅ Test release complete$(RESET)"
	@echo "$(BLUE)💡 Test installation: pip install -i https://test.pypi.org/simple/ $(PROJECT_NAME)$(RESET)"

release: build ## Release to PyPI (production)
	@echo "$(RED)⚠️  Releasing to production PyPI...$(RESET)"
	@echo "$(YELLOW)Current version: $$(make version)$(RESET)"
	@read -p "Confirm release to PyPI? (y/N): " confirm && [ "$$confirm" = "y" ]
	$(PYTHON) -m twine upload dist/*
	@echo "$(GREEN)🎉 Production release complete!$(RESET)"
	@echo "$(BLUE)📦 Package available at: https://pypi.org/project/$(PROJECT_NAME)/$(RESET)"

## Automated Release Workflow
release-patch: ## Bump patch version and trigger automated release
	@echo "$(GREEN)🚀 Starting automated patch release...$(RESET)"
	$(MAKE) dev-check
	$(MAKE) version-patch
	git push origin main --tags
	@echo "$(GREEN)✅ Release triggered! Monitor at: https://github.com/csmarshall/arris-modem-status/actions$(RESET)"

release-minor: ## Bump minor version and trigger automated release
	@echo "$(GREEN)🚀 Starting automated minor release...$(RESET)"
	$(MAKE) dev-check
	$(MAKE) version-minor
	git push origin main --tags
	@echo "$(GREEN)✅ Release triggered! Monitor at: https://github.com/csmarshall/arris-modem-status/actions$(RESET)"

## Development Utilities
install-dev: ## Install in development mode
	@echo "$(GREEN)📦 Installing in development mode...$(RESET)"
	$(PIP) install -e .[dev]
	@echo "$(GREEN)✅ Development installation complete$(RESET)"

install-deps: ## Install/upgrade all dependencies
	@echo "$(GREEN)📦 Installing dependencies...$(RESET)"
	$(PIP) install --upgrade pip wheel
	$(PIP) install -e .[dev,test,build]
	@echo "$(GREEN)✅ Dependencies installed$(RESET)"

pre-commit: ## Run pre-commit hooks manually
	@echo "$(GREEN)🔧 Running pre-commit hooks...$(RESET)"
	pre-commit run --all-files
	@echo "$(GREEN)✅ Pre-commit checks complete$(RESET)"

deps-show: ## Show current dependencies
	@echo "$(BLUE)📋 Current dependencies:$(RESET)"
	$(PIP) list

deps-outdated: ## Show outdated dependencies
	@echo "$(BLUE)📋 Outdated dependencies:$(RESET)"
	$(PIP) list --outdated

## CI/CD Simulation
ci-check: dev-check security ## Simulate CI/CD checks locally
	@echo "$(GREEN)🤖 Running CI/CD simulation...$(RESET)"
	@echo "$(GREEN)✅ All CI checks would pass - ready for push!$(RESET)"

## Quick Workflows
quick-fix: format lint ## Quick format and lint
	@echo "$(GREEN)⚡ Quick fix complete$(RESET)"

full-check: dev-check security build-check ## Complete validation including build
	@echo "$(GREEN)🎯 Full validation complete - ready for release!$(RESET)"

## Information
info: ## Show project information
	@echo "$(BLUE)📊 PROJECT INFORMATION$(RESET)"
	@echo "Project: $(PROJECT_NAME)"
	@echo "Version: $(make version)"
	@echo "Python: $($(PYTHON) --version)"
	@echo "Working Directory: $(pwd)"
	@echo "Virtual Environment: ${VIRTUAL_ENV:-Not activated}"
	@echo ""
	@echo "$(BLUE)📁 Project Structure:$(RESET)"
	@echo "Core Files:"
	@ls -la README.md LICENSE CHANGELOG.md pyproject.toml Makefile 2>/dev/null | sed 's/^/  /'
	@echo ""
	@echo "Configuration Files:"
	@ls -la .bumpversion.toml .pre-commit-config.yaml tox.ini 2>/dev/null | sed 's/^/  /'
	@echo ""
	@echo "Directories:"
	@ls -lad arris_modem_status/ tests/ scripts/ .github/ 2>/dev/null | sed 's/^/  /'
	@echo ""
	@echo "$(BLUE)📦 Build Status:$(RESET)"
	@if [ -d "dist/" ]; then echo "  ✅ Build artifacts: $(ls -1 dist/ | wc -l | tr -d ' ') files"; else echo "  ❌ No build artifacts (run 'make build')"; fi
	@if [ -d "htmlcov/" ]; then echo "  ✅ Coverage report available"; else echo "  ❌ No coverage report"; fi
	@echo ""
	@echo "$(BLUE)🔧 Development Status:$(RESET)"
	@if [ -f ".coverage" ]; then echo "  ✅ Tests have been run"; else echo "  ❌ No test coverage data"; fi
	@if command -v pre-commit >/dev/null 2>&1 && pre-commit --version >/dev/null 2>&1; then echo "  ✅ Pre-commit hooks installed"; else echo "  ❌ Pre-commit not configured"; fi
	@if [ -d "arris_modem_venv/" ] || [ -n "$VIRTUAL_ENV" ]; then echo "  ✅ Virtual environment active"; else echo "  ⚠️  No virtual environment detected"; fi
	@echo ""
	@echo "$(BLUE)🚀 Quick Commands:$(RESET)"
	@echo "  make dev-check    # Validate code quality"
	@echo "  make test         # Run full test suite"
	@echo "  make build        # Build for PyPI"
	@echo "  make release-patch # Automated patch release"
