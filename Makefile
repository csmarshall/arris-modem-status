# Makefile for arris-modem-status
# Provides convenient commands for development, testing, and release management
#
# Usage:
#   make help          # Show all available commands
#   make install       # Install package in development mode
#   make test          # Run tests
#   make format        # Format code
#   make lint          # Run linting
#   make version       # Show current version
#   make clean         # Clean build artifacts

.PHONY: help install test format lint clean build release version info
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Project variables
PACKAGE_NAME := arris-modem-status
PYTHON := python3
PIP := pip3
PROJECT_DIR := $(shell pwd)

help: ## Show this help message
	@echo "$(BLUE)arris-modem-status Development Commands$(RESET)"
	@echo ""
	@echo "$(YELLOW)Quick Start:$(RESET)"
	@echo "  $(BLUE)make setup-dev$(RESET)     # Setup development environment"
	@echo "  $(BLUE)make fix-build$(RESET)     # Fix build issues (run if 'make build' fails)"
	@echo "  $(BLUE)make dev-check$(RESET)     # Run complete development check"
	@echo ""
	@echo "$(YELLOW)All Commands:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)%-20s$(RESET) %s\n", $1, $2}'

install: ## Install package in development mode
	@echo "$(GREEN)Installing arris-modem-status in development mode...$(RESET)"
	$(PIP) install -e .[dev]
	@echo "$(GREEN)✅ Installation complete$(RESET)"

install-prod: ## Install package for production
	@echo "$(GREEN)Installing arris-modem-status for production...$(RESET)"
	$(PIP) install .
	@echo "$(GREEN)✅ Production installation complete$(RESET)"

test: ## Run all tests
	@echo "$(GREEN)Running tests...$(RESET)"
	pytest tests/ -v --cov=arris_modem_status --cov-report=term-missing
	@echo "$(GREEN)✅ Tests complete$(RESET)"

test-integration: ## Run integration tests (requires modem password)
	@echo "$(YELLOW)Running integration tests...$(RESET)"
	@if [ -z "$(PASSWORD)" ]; then \
		echo "$(RED)❌ Please provide PASSWORD: make test-integration PASSWORD=your_password$(RESET)"; \
		exit 1; \
	fi
	$(PYTHON) production_test.py --password "$(PASSWORD)" --comprehensive
	@echo "$(GREEN)✅ Integration tests complete$(RESET)"

format: ## Format code with Black and isort
	@echo "$(GREEN)Formatting Python code...$(RESET)"
	black arris_modem_status/ tests/ scripts/ --line-length 120
	isort arris_modem_status/ tests/ scripts/ --profile black --line-length 120
	@echo "$(GREEN)✅ Code formatting complete$(RESET)"

lint: ## Run all linting checks
	@echo "$(GREEN)Running linting checks...$(RESET)"
	flake8 arris_modem_status/ --max-line-length=120 --extend-ignore=E203,W503
	mypy arris_modem_status/ --ignore-missing-imports
	bandit -r arris_modem_status/ -ll
	@echo "$(GREEN)✅ Linting complete$(RESET)"

clean-whitespace: ## Clean up whitespace issues (PEP 8 compliance)
	@echo "$(GREEN)Cleaning whitespace issues...$(RESET)"
	$(PYTHON) scripts/manage_version.py --clean
	@echo "$(GREEN)✅ Whitespace cleanup complete$(RESET)"

migrate-setup-cfg: ## Migrate setup.cfg to modern pyproject.toml
	@echo "$(GREEN)Migrating setup.cfg configuration...$(RESET)"
	$(PYTHON) scripts/migrate_setup_cfg.py --migrate
	@echo "$(GREEN)✅ setup.cfg migration complete$(RESET)"

check-setup-cfg: ## Check setup.cfg for version conflicts
	@echo "$(GREEN)Checking setup.cfg for conflicts...$(RESET)"
	$(PYTHON) scripts/migrate_setup_cfg.py --analyze

version: ## Show current version
	@echo "$(BLUE)Current version information:$(RESET)"
	@$(PYTHON) scripts/manage_version.py --current

version-info: ## Show detailed version information
	@$(PYTHON) scripts/manage_version.py --info

version-bump-patch: ## Bump patch version (1.3.0 -> 1.3.1)
	@echo "$(GREEN)Bumping patch version...$(RESET)"
	$(PYTHON) scripts/manage_version.py --bump patch
	@echo "$(GREEN)✅ Patch version bumped$(RESET)"

version-bump-minor: ## Bump minor version (1.3.0 -> 1.4.0)
	@echo "$(GREEN)Bumping minor version...$(RESET)"
	$(PYTHON) scripts/manage_version.py --bump minor
	@echo "$(GREEN)✅ Minor version bumped$(RESET)"

version-bump-major: ## Bump major version (1.3.0 -> 2.0.0)
	@echo "$(YELLOW)Bumping major version (breaking changes)...$(RESET)"
	$(PYTHON) scripts/manage_version.py --bump major
	@echo "$(GREEN)✅ Major version bumped$(RESET)"

version-set: ## Set specific version (usage: make version-set VERSION=1.3.1)
	@if [ -z "$(VERSION)" ]; then \
		echo "$(RED)❌ Please provide VERSION: make version-set VERSION=1.3.1$(RESET)"; \
		exit 1; \
	fi
	@echo "$(GREEN)Setting version to $(VERSION)...$(RESET)"
	$(PYTHON) scripts/manage_version.py --set $(VERSION)
	@echo "$(GREEN)✅ Version set to $(VERSION)$(RESET)"

validate: ## Validate version consistency and code quality
	@echo "$(GREEN)Validating project consistency...$(RESET)"
	$(PYTHON) scripts/manage_version.py --validate
	@echo "$(GREEN)✅ Validation complete$(RESET)"

clean: ## Clean build artifacts and cache files
	@echo "$(GREEN)Cleaning build artifacts...$(RESET)"
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "$(GREEN)✅ Cleanup complete$(RESET)"

build: clean ## Build distribution packages
	@echo "$(GREEN)Building distribution packages...$(RESET)"
	@if ! $(PYTHON) -c "import build" 2>/dev/null; then \
		echo "$(RED)❌ Build package not found. Installing build dependencies...$(RESET)"; \
		$(PIP) install build twine wheel; \
	fi
	$(PYTHON) -m build
	@echo "$(GREEN)✅ Build complete$(RESET)"

build-check: ## Check build artifacts
	@echo "$(GREEN)Checking build artifacts...$(RESET)"
	@if ! $(PYTHON) -c "import twine" 2>/dev/null; then \
		echo "$(RED)❌ Twine not found. Installing...$(RESET)"; \
		$(PIP) install twine; \
	fi
	$(PYTHON) -m twine check dist/*
	@echo "$(GREEN)✅ Build check complete$(RESET)"

install-build-deps: ## Install build dependencies
	@echo "$(GREEN)Installing build dependencies...$(RESET)"
	$(PIP) install build twine wheel
	@echo "$(GREEN)✅ Build dependencies installed$(RESET)"

fix-build: ## Fix build dependency issues automatically
	@echo "$(GREEN)Fixing build dependencies...$(RESET)"
	$(PYTHON) scripts/fix_build_deps.py
	@echo "$(GREEN)✅ Build dependencies fixed$(RESET)"

release-test: build build-check ## Test release to TestPyPI
	@echo "$(YELLOW)Uploading to TestPyPI...$(RESET)"
	$(PYTHON) -m twine upload --repository testpypi dist/*
	@echo "$(GREEN)✅ Test release complete$(RESET)"

release: build build-check ## Release to PyPI (production)
	@echo "$(RED)⚠️  Releasing to production PyPI...$(RESET)"
	@read -p "Are you sure you want to release to PyPI? (y/N): " confirm && [ "$$confirm" = "y" ]
	$(PYTHON) -m twine upload dist/*
	@echo "$(GREEN)✅ Production release complete$(RESET)"

setup-dev: ## Setup development environment
	@echo "$(GREEN)Setting up development environment...$(RESET)"
	$(PIP) install -e .[dev,build]
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
		echo "$(GREEN)✅ Pre-commit hooks installed$(RESET)"; \
	else \
		echo "$(YELLOW)⚠️  Pre-commit not available, installing...$(RESET)"; \
		$(PIP) install pre-commit; \
		pre-commit install; \
	fi
	@echo "$(GREEN)✅ Development environment ready$(RESET)"

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(GREEN)Running pre-commit hooks...$(RESET)"
	pre-commit run --all-files
	@echo "$(GREEN)✅ Pre-commit checks complete$(RESET)"

docs: ## Generate documentation (placeholder)
	@echo "$(BLUE)Documentation generation not yet implemented$(RESET)"
	@echo "$(BLUE)See README.md for usage instructions$(RESET)"

# Development workflow shortcuts
dev-check: format lint test ## Run complete development check (format, lint, test)
	@echo "$(GREEN)✅ Development check complete - ready for commit$(RESET)"

quick-test: ## Quick test without coverage
	@echo "$(GREEN)Running quick tests...$(RESET)"
	pytest tests/ -x -q
	@echo "$(GREEN)✅ Quick tests complete$(RESET)"

# CI/CD related commands
ci-check: lint test ## Run CI checks locally
	@echo "$(GREEN)Running CI checks locally...$(RESET)"
	@echo "$(GREEN)✅ CI checks complete$(RESET)"

# Utility commands
show-deps: ## Show current dependencies
	@echo "$(BLUE)Current dependencies:$(RESET)"
	$(PIP) list

outdated: ## Show outdated dependencies
	@echo "$(BLUE)Outdated dependencies:$(RESET)"
	$(PIP) list --outdated

security-check: ## Run security audit
	@echo "$(GREEN)Running security audit...$(RESET)"
	$(PIP) audit
	@echo "$(GREEN)✅ Security audit complete$(RESET)"