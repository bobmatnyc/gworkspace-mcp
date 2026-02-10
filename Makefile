# ============================================================================
# Google Workspace MCP Server - Makefile
# ============================================================================
# Automates development, testing, and publishing workflows
#
# Quick start:
#   make help      - Show this help
#   make install   - Install package in dev mode
#   make test      - Run pytest
#   make build     - Build wheel and sdist
#   make publish-pypi - Publish to PyPI

# ============================================================================
# PHONY Target Declarations
# ============================================================================
.PHONY: help install install-dev test lint format clean build
.PHONY: publish-pypi pre-publish sync-versions
.PHONY: release-patch release-minor release-major auto-patch

# ============================================================================
# Shell Configuration (Strict Mode)
# ============================================================================
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules

# ============================================================================
# Configuration Variables
# ============================================================================
# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Build directories
BUILD_DIR := build
DIST_DIR := dist
PYTHON := python3

# Default target
all: help

# ============================================================================
# Help System
# ============================================================================

help: ## Show this help message
	@echo "Google Workspace MCP Server - Makefile"
	@echo "======================================"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "$(BLUE)Quick Commands:$(NC)"
	@echo "  $(GREEN)make install$(NC)      - Install package in dev mode"
	@echo "  $(GREEN)make test$(NC)         - Run pytest"
	@echo "  $(GREEN)make lint$(NC)         - Run ruff linter"
	@echo "  $(GREEN)make format$(NC)       - Format code with ruff"
	@echo "  $(GREEN)make build$(NC)        - Build wheel and sdist"
	@echo "  $(GREEN)make publish-pypi$(NC) - Publish to PyPI"
	@echo ""
	@echo "$(BLUE)All Available Targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BLUE)Version:$(NC) $$(cat VERSION 2>/dev/null || echo 'unknown')"
	@echo "$(BLUE)Build:$(NC)   $$(cat BUILD_NUMBER 2>/dev/null || echo 'unknown')"

# ============================================================================
# Installation Targets
# ============================================================================

install: ## Install package in development mode
	@echo "$(YELLOW)Installing google-workspace-mcp in dev mode...$(NC)"
	@pip install -e .
	@echo "$(GREEN)Done. Run 'workspace --help' to verify.$(NC)"

install-dev: ## Install package with dev dependencies
	@echo "$(YELLOW)Installing google-workspace-mcp with dev dependencies...$(NC)"
	@pip install -e ".[dev]"
	@echo "$(GREEN)Done.$(NC)"

# ============================================================================
# Testing Targets
# ============================================================================

test: ## Run pytest
	@echo "$(YELLOW)Running tests...$(NC)"
	@python -m pytest tests/ -v
	@echo "$(GREEN)Tests completed.$(NC)"

test-cov: ## Run pytest with coverage
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	@python -m pytest tests/ -v --cov=src/google_workspace_mcp --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report generated in htmlcov/$(NC)"

# ============================================================================
# Linting & Formatting
# ============================================================================

lint: ## Run ruff linter
	@echo "$(YELLOW)Running ruff linter...$(NC)"
	@if command -v ruff &> /dev/null; then \
		ruff check src/ tests/ || exit 1; \
		echo "$(GREEN)Linting passed.$(NC)"; \
	else \
		echo "$(RED)ruff not found. Install with: pip install ruff$(NC)"; \
		exit 1; \
	fi

format: ## Format code with ruff
	@echo "$(YELLOW)Formatting code...$(NC)"
	@if command -v ruff &> /dev/null; then \
		ruff check src/ tests/ --fix || true; \
		ruff format src/ tests/; \
		echo "$(GREEN)Formatting complete.$(NC)"; \
	else \
		echo "$(RED)ruff not found. Install with: pip install ruff$(NC)"; \
		exit 1; \
	fi

type-check: ## Run mypy type checker
	@echo "$(YELLOW)Running type checks...$(NC)"
	@if command -v mypy &> /dev/null; then \
		mypy src/ --ignore-missing-imports || true; \
		echo "$(GREEN)Type check complete.$(NC)"; \
	else \
		echo "$(YELLOW)mypy not found. Install with: pip install mypy$(NC)"; \
	fi

# ============================================================================
# Cleanup Targets
# ============================================================================

clean: ## Remove build artifacts
	@echo "$(YELLOW)Cleaning build artifacts...$(NC)"
	@rm -rf $(BUILD_DIR) $(DIST_DIR) *.egg-info src/*.egg-info
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -name ".DS_Store" -delete 2>/dev/null || true
	@echo "$(GREEN)Clean complete.$(NC)"

# ============================================================================
# Build Targets
# ============================================================================

build: clean ## Build wheel and sdist
	@echo "$(YELLOW)Building package...$(NC)"
	@if command -v uv &> /dev/null; then \
		uv build; \
	else \
		python -m build; \
	fi
	@echo "$(GREEN)Build complete.$(NC)"
	@ls -la $(DIST_DIR)/

# ============================================================================
# Version Management
# ============================================================================

sync-versions: ## Sync VERSION files across the project
	@echo "$(YELLOW)Syncing version files...$(NC)"
	@VERSION=$$(cat VERSION); \
	echo "$$VERSION" > src/google_workspace_mcp/VERSION; \
	sed -i '' "s/__version__ = \".*\"/__version__ = \"$$VERSION\"/" src/google_workspace_mcp/__version__.py 2>/dev/null || \
	sed -i "s/__version__ = \".*\"/__version__ = \"$$VERSION\"/" src/google_workspace_mcp/__version__.py; \
	echo "$(GREEN)Synced to version $$VERSION$(NC)"

release-patch: ## Bump patch version (x.y.Z+1)
	@echo "$(YELLOW)Bumping patch version...$(NC)"
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	PATCH=$$(echo $$VERSION | cut -d. -f3); \
	NEW_PATCH=$$((PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"
	@$(MAKE) sync-versions

release-minor: ## Bump minor version (x.Y+1.0)
	@echo "$(YELLOW)Bumping minor version...$(NC)"
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	NEW_MINOR=$$((MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"
	@$(MAKE) sync-versions

release-major: ## Bump major version (X+1.0.0)
	@echo "$(YELLOW)Bumping major version...$(NC)"
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	NEW_MAJOR=$$((MAJOR + 1)); \
	NEW_VERSION="$$NEW_MAJOR.0.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"
	@$(MAKE) sync-versions

# ============================================================================
# Publishing Targets
# ============================================================================

pre-publish: lint test ## Run quality checks before publishing
	@echo "$(BLUE)============================================$(NC)"
	@echo "$(BLUE)Pre-Publish Quality Gate$(NC)"
	@echo "$(BLUE)============================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Checking working directory...$(NC)"
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(YELLOW)Warning: Working directory has uncommitted changes$(NC)"; \
	else \
		echo "$(GREEN)Working directory is clean.$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)============================================$(NC)"
	@echo "$(GREEN)Pre-publish checks PASSED!$(NC)"
	@echo "$(GREEN)============================================$(NC)"

publish-pypi: pre-publish build ## Publish to PyPI
	@echo "$(YELLOW)Publishing to PyPI...$(NC)"
	@./scripts/publish_to_pypi.sh

auto-patch: pre-publish release-patch build ## Automated patch release (bump, build, ready to publish)
	@echo ""
	@echo "$(GREEN)============================================$(NC)"
	@echo "$(GREEN)Patch release ready!$(NC)"
	@echo "$(GREEN)============================================$(NC)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Review the changes"
	@echo "  2. Commit: git add -A && git commit -m 'chore: release v$$(cat VERSION)'"
	@echo "  3. Tag: git tag v$$(cat VERSION)"
	@echo "  4. Push: git push && git push --tags"
	@echo "  5. Publish: make publish-pypi"
