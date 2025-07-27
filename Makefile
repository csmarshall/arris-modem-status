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
	@echo "  $(BLUE)make dev-check$(RESET)     # Run complete development check"
	@echo ""
	@echo "$(YELLOW)All Commands:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | while read -r line; do \
		target=$$(echo "$$line" | cut -d':' -f1); \
		desc=$$(echo "$$line" | sed 's/^[^:]*:.*## //'); \
		printf "$(BLUE)%-20s$(RESET) %s\n" "$$target" "$$desc"; \
	done

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
	# Use pytest markers for integration tests
	$(PYTHON) -m pytest tests/ -m integration -v
	@echo "$(GREEN)✅ Integration tests complete$(RESET)"

test-quick: ## Quick test without coverage
	@echo "$(GREEN)Running quick tests...$(RESET)"
	pytest tests/ -x -q -m "not integration"
	@echo "$(GREEN)✅ Quick tests complete$(RESET)"

format: ## Format code with Black, isort, and autopep8
	@echo "$(GREEN)Formatting Python code...$(RESET)"
	# Black handles most formatting including whitespace
	black arris_modem_status/ tests/ --line-length 120
	# isort handles import sorting
	isort arris_modem_status/ tests/ --profile black --line-length 120
	# autopep8 for any remaining PEP8 issues (whitespace, etc)
	autopep8 --in-place --recursive --max-line-length 120 arris_modem_status/ tests/
	@echo "$(GREEN)✅ Code formatting complete$(RESET)"

format-check: ## Check formatting without changing files
	@echo "$(GREEN)Checking code formatting...$(RESET)"
	black --check arris_modem_status/ tests/ --line-length 120
	isort --check-only arris_modem_status/ tests/ --profile black --line-length 120
	@echo "$(GREEN)✅ Format check complete$(RESET)"

fix-whitespace: ## Fix whitespace issues specifically
	@echo "$(GREEN)Fixing whitespace issues...$(RESET)"
	# Remove trailing whitespace
	find arris_modem_status tests -name "*.py" -type f -exec sed -i '' 's/[[:space:]]*$$//' {} \;
	# Ensure files end with newline
	find arris_modem_status tests -name "*.py" -type f -exec sh -c 'tail -c1 {} | read -r _ || echo >> {}' \;
	# Fix tabs to spaces
	find arris_modem_status tests -name "*.py" -type f -exec sed -i '' 's/\t/    /g' {} \;
	@echo "$(GREEN)✅ Whitespace cleanup complete$(RESET)"

fix-all: ## Fix all formatting, whitespace, and PEP8 issues
	@echo "$(GREEN)🔧 Running complete code cleanup...$(RESET)"
	# Run all formatters
	$(MAKE) format
	# Run pre-commit to catch anything else
	pre-commit run --all-files || true
	# Final validation
	$(MAKE) lint
	@echo "$(GREEN)✅ All code issues fixed!$(RESET)"

pep8-report: ## Generate detailed PEP8 compliance report
	@echo "$(GREEN)Generating PEP8 compliance report...$(RESET)"
	flake8 arris_modem_status/ tests/ --max-line-length=120 --extend-ignore=E203,E501,W503 --statistics --output-file=pep8-report.txt
	@echo "$(GREEN)✅ Report saved to pep8-report.txt$(RESET)"

lint: ## Run all linting checks
	@echo "$(GREEN)Running linting checks...$(RESET)"
	flake8 arris_modem_status/ --max-line-length=120 --extend-ignore=E203,E501,W503
	mypy arris_modem_status/ --ignore-missing-imports
	bandit -r arris_modem_status/ -ll
	@echo "$(GREEN)✅ Linting complete$(RESET)"

flake8-report: ## Generate comprehensive flake8 report
	@echo "$(GREEN)Running comprehensive flake8 analysis...$(RESET)"
	@echo "======================================"
	# Basic check
	@flake8 arris_modem_status tests --count --statistics || true
	@echo ""
	@echo "$(BLUE)Code Complexity Report:$(RESET)"
	@flake8 arris_modem_status --max-complexity=10 --select=C901 || true
	@echo ""
	@echo "$(BLUE)Import Issues:$(RESET)"
	@flake8 arris_modem_status tests --select=F401,F402,F403,F404 || true
	@echo ""
	@echo "$(BLUE)Naming Conventions:$(RESET)"
	@flake8 arris_modem_status --select=N8 || true
	@echo ""
	@echo "$(BLUE)Documentation Issues:$(RESET)"
	@flake8 arris_modem_status --select=D || true
	@echo "======================================"
	@echo "$(GREEN)✅ Flake8 analysis complete$(RESET)"

flake8-strict: ## Run flake8 with strict settings
	@echo "$(GREEN)Running strict flake8 checks...$(RESET)"
	flake8 arris_modem_status tests --max-line-length=79 --max-complexity=5 --select=E,W,F,C,N

version: ## Show current version
	@echo "$(BLUE)Current version:$(RESET)"
	@grep -E '^__version__' arris_modem_status/__init__.py | cut -d'"' -f2

version-bump-patch: ## Bump patch version (1.3.0 -> 1.3.1)
	@echo "$(GREEN)Bumping patch version...$(RESET)"
	bump-my-version bump patch
	@echo "$(GREEN)✅ Patch version bumped$(RESET)"

version-bump-minor: ## Bump minor version (1.3.0 -> 1.4.0)
	@echo "$(GREEN)Bumping minor version...$(RESET)"
	bump-my-version bump minor
	@echo "$(GREEN)✅ Minor version bumped$(RESET)"

version-bump-major: ## Bump major version (1.3.0 -> 2.0.0)
	@echo "$(YELLOW)Bumping major version (breaking changes)...$(RESET)"
	bump-my-version bump major
	@echo "$(GREEN)✅ Major version bumped$(RESET)"

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
	$(PIP) install build twine wheel bump-my-version
	@echo "$(GREEN)✅ Build dependencies installed$(RESET)"

check-deps: ## Check for missing dependencies
	@echo "$(GREEN)Checking dependencies...$(RESET)"
	$(PIP) check
	@echo "$(GREEN)✅ Dependency check complete$(RESET)"

release-test: build build-check ## Test release to TestPyPI
	@echo "$(YELLOW)Uploading to TestPyPI...$(RESET)"
	$(PYTHON) -m twine upload --repository testpypi dist/*
	@echo "$(GREEN)✅ Test release complete$(RESET)"

release: build build-check ## Release to PyPI (production)
	@echo "$(RED)⚠️  Releasing to production PyPI...$(RESET)"
	@read -p "Are you sure you want to release to PyPI? (y/N): " confirm && [ "$$confirm" = "y" ]
	$(PYTHON) -m twine upload dist/*
	@echo "$(GREEN)✅ Production release complete$(RESET)"

setup-dev: ## Setup development environment with pre-commit
	@echo "$(GREEN)Setting up development environment...$(RESET)"
	$(PIP) install -e .[dev,build]
	# Install and setup pre-commit hooks
	pre-commit install
	pre-commit install --hook-type pre-push
	@echo "$(GREEN)✅ Pre-commit hooks installed$(RESET)"
	@echo "$(BLUE)ℹ️  Code will be auto-formatted on every commit$(RESET)"
	@echo "$(GREEN)✅ Development environment ready$(RESET)"

pre-commit-run: ## Run pre-commit on all files manually
	@echo "$(GREEN)Running pre-commit hooks on all files...$(RESET)"
	pre-commit run --all-files
	@echo "$(GREEN)✅ Pre-commit checks complete$(RESET)"

pre-commit-install: ## Install pre-commit hooks (including pre-push)
	@echo "$(GREEN)Installing pre-commit hooks...$(RESET)"
	pre-commit install --hook-type pre-commit
	pre-commit install --hook-type pre-push
	@echo "$(GREEN)✅ Pre-commit and pre-push hooks installed$(RESET)"

pre-commit-update: ## Update pre-commit hooks to latest versions
	@echo "$(GREEN)Updating pre-commit hooks...$(RESET)"
	pre-commit autoupdate
	@echo "$(GREEN)✅ Pre-commit hooks updated$(RESET)"

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
