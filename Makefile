# ============================================================================
# Google Workspace MCP Server - Makefile
# ============================================================================
# Automates development, testing, and publishing workflows
#
# Quick start:
#   make help         - Show this help
#   make install      - Install package in dev mode
#   make test         - Run pytest
#   make build        - Build wheel and sdist
#   make publish-pypi - Publish to PyPI
#
# Version & Release:
#   make version      - Show current version
#   make bump-patch   - Bump patch version (0.1.21 -> 0.1.22)
#   make bump-minor   - Bump minor version (0.1.21 -> 0.2.0)
#   make bump-major   - Bump major version (0.1.21 -> 1.0.0)
#   make release-patch - Full release: bump patch + commit + tag + push

# ============================================================================
# PHONY Target Declarations
# ============================================================================
.PHONY: help install install-dev test lint format clean build
.PHONY: publish publish-minor publish-major publish-only publish-pypi pre-publish sync-versions
.PHONY: release-patch release-minor release-major auto-patch
.PHONY: version bump-patch bump-minor bump-major
.PHONY: tag push push-tags
.PHONY: homebrew-update homebrew-test homebrew-dry-run

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
PYTHON := uv run python

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
	@echo "$(BLUE)Version Management:$(NC)"
	@echo "  $(GREEN)make version$(NC)       - Show current version"
	@echo "  $(GREEN)make bump-patch$(NC)    - Bump patch version (x.y.Z+1)"
	@echo "  $(GREEN)make bump-minor$(NC)    - Bump minor version (x.Y+1.0)"
	@echo "  $(GREEN)make bump-major$(NC)    - Bump major version (X+1.0.0)"
	@echo ""
	@echo "$(BLUE)Publishing (Unified System):$(NC)"
	@echo "  $(GREEN)make publish$(NC)       - Patch version + PyPI + GitHub + Homebrew"
	@echo "  $(GREEN)make publish-minor$(NC) - Minor version + PyPI + GitHub + Homebrew"
	@echo "  $(GREEN)make publish-major$(NC) - Major version + PyPI + GitHub + Homebrew"
	@echo "  $(GREEN)make publish-only$(NC)  - Publish current version to PyPI only"
	@echo ""
	@echo "$(BLUE)Git Operations:$(NC)"
	@echo "  $(GREEN)make tag$(NC)           - Create git tag for current version"
	@echo "  $(GREEN)make push$(NC)          - Push commits to origin"
	@echo "  $(GREEN)make push-tags$(NC)     - Push tags to origin"
	@echo "  $(GREEN)make release-patch$(NC) - Legacy: bump + commit + tag + push (use publish)"
	@echo "  $(GREEN)make release-minor$(NC) - Legacy: bump minor + commit + tag + push (use publish-minor)"
	@echo ""
	@echo "$(BLUE)Development:$(NC)"
	@echo "  $(GREEN)make install$(NC)       - Install package in dev mode"
	@echo "  $(GREEN)make test$(NC)          - Run pytest"
	@echo "  $(GREEN)make lint$(NC)          - Run ruff linter"
	@echo "  $(GREEN)make format$(NC)        - Format code with ruff"
	@echo "  $(GREEN)make build$(NC)         - Build wheel and sdist"
	@echo "  $(GREEN)make clean$(NC)         - Remove build artifacts"
	@echo ""
	@echo "$(BLUE)Homebrew:$(NC)"
	@echo "  $(GREEN)make homebrew-dry-run$(NC) - Test Homebrew update (safe)"
	@echo "  $(GREEN)make homebrew-update$(NC)  - Update Homebrew formula"
	@echo "  $(GREEN)make homebrew-test$(NC)    - Test local Homebrew install"
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
	@echo "$(YELLOW)Installing gworkspace-mcp in dev mode...$(NC)"
	@pip install -e .
	@echo "$(GREEN)Done. Run 'workspace --help' to verify.$(NC)"

install-dev: ## Install package with dev dependencies
	@echo "$(YELLOW)Installing gworkspace-mcp with dev dependencies...$(NC)"
	@pip install -e ".[dev]"
	@echo "$(GREEN)Done.$(NC)"

# ============================================================================
# Testing Targets
# ============================================================================

test: ## Run pytest
	@echo "$(YELLOW)Running tests...$(NC)"
	@$(PYTHON) -m pytest tests/ -v
	@echo "$(GREEN)Tests completed.$(NC)"

test-cov: ## Run pytest with coverage
	@echo "$(YELLOW)Running tests with coverage...$(NC)"
	@python -m pytest tests/ -v --cov=src/gworkspace_mcp --cov-report=html --cov-report=term
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

version: ## Show current version
	@cat VERSION

sync-versions: ## Sync VERSION files across the project
	@echo "$(YELLOW)Syncing version files...$(NC)"
	@VERSION=$$(cat VERSION); \
	echo "$$VERSION" > src/gworkspace_mcp/VERSION; \
	sed -i '' "s/^version = \"[^\"]*\"/version = \"$$VERSION\"/" pyproject.toml 2>/dev/null || \
	sed -i "s/^version = \"[^\"]*\"/version = \"$$VERSION\"/" pyproject.toml; \
	sed -i '' "s/^__version__ = \"[^\"]*\"/__version__ = \"$$VERSION\"/" src/gworkspace_mcp/__version__.py 2>/dev/null || \
	sed -i "s/^__version__ = \"[^\"]*\"/__version__ = \"$$VERSION\"/" src/gworkspace_mcp/__version__.py; \
	echo "$(GREEN)Synced to version $$VERSION$(NC)"

bump-patch: ## Bump patch version (x.y.Z+1), updates all version files
	@echo "$(YELLOW)Bumping patch version...$(NC)"
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(RED)Error: Working directory is not clean. Commit or stash changes first.$(NC)"; \
		exit 1; \
	fi
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	PATCH=$$(echo $$VERSION | cut -d. -f3); \
	NEW_PATCH=$$((PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"
	@$(MAKE) sync-versions

bump-minor: ## Bump minor version (x.Y+1.0), updates all version files
	@echo "$(YELLOW)Bumping minor version...$(NC)"
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(RED)Error: Working directory is not clean. Commit or stash changes first.$(NC)"; \
		exit 1; \
	fi
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	NEW_MINOR=$$((MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"
	@$(MAKE) sync-versions

bump-major: ## Bump major version (X+1.0.0), updates all version files
	@echo "$(YELLOW)Bumping major version...$(NC)"
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(RED)Error: Working directory is not clean. Commit or stash changes first.$(NC)"; \
		exit 1; \
	fi
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	NEW_MAJOR=$$((MAJOR + 1)); \
	NEW_VERSION="$$NEW_MAJOR.0.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"
	@$(MAKE) sync-versions

# ============================================================================
# Git Operations
# ============================================================================

tag: ## Create git tag for current version
	@VERSION=$$(cat VERSION); \
	echo "$(YELLOW)Creating tag v$$VERSION...$(NC)"; \
	git tag -a "v$$VERSION" -m "Release v$$VERSION"; \
	echo "$(GREEN)Tag v$$VERSION created$(NC)"

push: ## Push commits to origin
	@echo "$(YELLOW)Pushing commits to origin...$(NC)"
	@git push origin
	@echo "$(GREEN)Commits pushed$(NC)"

push-tags: ## Push tags to origin
	@echo "$(YELLOW)Pushing tags to origin...$(NC)"
	@git push origin --tags
	@echo "$(GREEN)Tags pushed$(NC)"


# ============================================================================
# Full Release Workflows
# ============================================================================

release-patch: ## Full release: bump patch + commit + tag + push all
	@echo "$(BLUE)============================================$(NC)"
	@echo "$(BLUE)Starting Patch Release$(NC)"
	@echo "$(BLUE)============================================$(NC)"
	@# Check clean working directory
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(RED)Error: Working directory is not clean. Commit or stash changes first.$(NC)"; \
		exit 1; \
	fi
	@# Check we're on main branch
	@BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	if [ "$$BRANCH" != "main" ]; then \
		echo "$(YELLOW)Warning: Not on main branch (currently on $$BRANCH)$(NC)"; \
		read -p "Continue anyway? [y/N] " confirm; \
		if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
			echo "$(RED)Aborted.$(NC)"; \
			exit 1; \
		fi; \
	fi
	@# Bump version
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	PATCH=$$(echo $$VERSION | cut -d. -f3); \
	NEW_PATCH=$$((PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$$NEW_VERSION" > src/gworkspace_mcp/VERSION; \
	sed -i '' "s/^version = \"[^\"]*\"/version = \"$$NEW_VERSION\"/" pyproject.toml 2>/dev/null || \
	sed -i "s/^version = \"[^\"]*\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"; \
	echo "$(YELLOW)Creating commit...$(NC)"; \
	git add VERSION src/gworkspace_mcp/VERSION pyproject.toml; \
	git commit -m "chore: Bump version to $$NEW_VERSION"; \
	echo "$(YELLOW)Creating tag...$(NC)"; \
	git tag -a "v$$NEW_VERSION" -m "Release v$$NEW_VERSION"; \
	echo "$(YELLOW)Pushing to origin...$(NC)"; \
	git push origin; \
	git push origin --tags; \
	echo ""; \
	echo "$(GREEN)============================================$(NC)"; \
	echo "$(GREEN)Release v$$NEW_VERSION complete!$(NC)"; \
	echo "$(GREEN)============================================$(NC)"

release-minor: ## Full release: bump minor + commit + tag + push all
	@echo "$(BLUE)============================================$(NC)"
	@echo "$(BLUE)Starting Minor Release$(NC)"
	@echo "$(BLUE)============================================$(NC)"
	@# Check clean working directory
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(RED)Error: Working directory is not clean. Commit or stash changes first.$(NC)"; \
		exit 1; \
	fi
	@# Check we're on main branch
	@BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	if [ "$$BRANCH" != "main" ]; then \
		echo "$(YELLOW)Warning: Not on main branch (currently on $$BRANCH)$(NC)"; \
		read -p "Continue anyway? [y/N] " confirm; \
		if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
			echo "$(RED)Aborted.$(NC)"; \
			exit 1; \
		fi; \
	fi
	@# Bump version
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	NEW_MINOR=$$((MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$$NEW_VERSION" > src/gworkspace_mcp/VERSION; \
	sed -i '' "s/^version = \"[^\"]*\"/version = \"$$NEW_VERSION\"/" pyproject.toml 2>/dev/null || \
	sed -i "s/^version = \"[^\"]*\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"; \
	echo "$(YELLOW)Creating commit...$(NC)"; \
	git add VERSION src/gworkspace_mcp/VERSION pyproject.toml; \
	git commit -m "chore: Bump version to $$NEW_VERSION"; \
	echo "$(YELLOW)Creating tag...$(NC)"; \
	git tag -a "v$$NEW_VERSION" -m "Release v$$NEW_VERSION"; \
	echo "$(YELLOW)Pushing to origin...$(NC)"; \
	git push origin; \
	git push origin --tags; \
	echo ""; \
	echo "$(GREEN)============================================$(NC)"; \
	echo "$(GREEN)Release v$$NEW_VERSION complete!$(NC)"; \
	echo "$(GREEN)============================================$(NC)"

release-major: ## Full release: bump major + commit + tag + push all
	@echo "$(BLUE)============================================$(NC)"
	@echo "$(BLUE)Starting Major Release$(NC)"
	@echo "$(BLUE)============================================$(NC)"
	@# Check clean working directory
	@if [ -n "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(RED)Error: Working directory is not clean. Commit or stash changes first.$(NC)"; \
		exit 1; \
	fi
	@# Check we're on main branch
	@BRANCH=$$(git rev-parse --abbrev-ref HEAD); \
	if [ "$$BRANCH" != "main" ]; then \
		echo "$(YELLOW)Warning: Not on main branch (currently on $$BRANCH)$(NC)"; \
		read -p "Continue anyway? [y/N] " confirm; \
		if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
			echo "$(RED)Aborted.$(NC)"; \
			exit 1; \
		fi; \
	fi
	@# Bump version
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	NEW_MAJOR=$$((MAJOR + 1)); \
	NEW_VERSION="$$NEW_MAJOR.0.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "$$NEW_VERSION" > src/gworkspace_mcp/VERSION; \
	sed -i '' "s/^version = \"[^\"]*\"/version = \"$$NEW_VERSION\"/" pyproject.toml 2>/dev/null || \
	sed -i "s/^version = \"[^\"]*\"/version = \"$$NEW_VERSION\"/" pyproject.toml; \
	echo "$(GREEN)Version bumped: $$VERSION -> $$NEW_VERSION$(NC)"; \
	echo "$(YELLOW)Creating commit...$(NC)"; \
	git add VERSION src/gworkspace_mcp/VERSION pyproject.toml; \
	git commit -m "chore: Bump version to $$NEW_VERSION"; \
	echo "$(YELLOW)Creating tag...$(NC)"; \
	git tag -a "v$$NEW_VERSION" -m "Release v$$NEW_VERSION"; \
	echo "$(YELLOW)Pushing to origin...$(NC)"; \
	git push origin; \
	git push origin --tags; \
	echo ""; \
	echo "$(GREEN)============================================$(NC)"; \
	echo "$(GREEN)Release v$$NEW_VERSION complete!$(NC)"; \
	echo "$(GREEN)============================================$(NC)"

# ============================================================================
# Unified Publishing System
# ============================================================================
# Adapted from mcp-vector-search publishing patterns
# Single command publishes to PyPI, GitHub Releases, and Homebrew

VERSION_PY := src/gworkspace_mcp/__version__.py

# Get current version from __version__.py
get-version = $(shell grep -E '^__version__' $(VERSION_PY) | sed 's/.*"\(.*\)"/\1/')

.PHONY: publish publish-minor publish-major publish-only pre-publish

publish: ## Bump patch version, build, publish to PyPI, tag, and push
	@echo "$(BLUE)═══════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  Publishing Patch Release$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════$(NC)"
	@$(MAKE) pre-publish
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	PATCH=$$(echo $$CURRENT | cut -d. -f3); \
	NEW_PATCH=$$((PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	echo "$(YELLOW)Version: $$CURRENT → $$NEW_VERSION$(NC)"; \
	echo "$$NEW_VERSION" > VERSION; \
	$(MAKE) sync-versions; \
	echo "$(GREEN)✓ Version bumped$(NC)"; \
	git add VERSION src/gworkspace_mcp/VERSION pyproject.toml src/gworkspace_mcp/__version__.py; \
	git commit -m "chore: bump version to $$NEW_VERSION"; \
	echo "$(GREEN)✓ Committed$(NC)"; \
	git tag "v$$NEW_VERSION"; \
	echo "$(GREEN)✓ Tagged v$$NEW_VERSION$(NC)"; \
	git push && git push --tags; \
	echo "$(GREEN)✓ Pushed to origin$(NC)"; \
	rm -rf dist/; \
	$(MAKE) build; \
	echo "$(GREEN)✓ Built package$(NC)"; \
	if [ -f .env.local ]; then \
		. .env.local && UV_PUBLISH_TOKEN="$$PYPI_TOKEN" $(PYTHON) -m twine upload dist/*; \
		echo "$(GREEN)✓ Published to PyPI$(NC)"; \
	else \
		echo "$(RED)✗ .env.local not found - set PYPI_TOKEN$(NC)"; \
		exit 1; \
	fi; \
	if command -v gh >/dev/null 2>&1; then \
		gh release create "v$$NEW_VERSION" \
			--title "v$$NEW_VERSION" \
			--generate-notes \
			dist/* || echo "$(YELLOW)⚠ GitHub CLI not available - skipping release$(NC)"; \
		echo "$(GREEN)✓ GitHub Release created$(NC)"; \
	else \
		echo "$(YELLOW)⚠ GitHub CLI not available - skipping release$(NC)"; \
	fi; \
	if [ -f .env.local ]; then \
		. .env.local; \
	fi; \
	if [ -z "$$HOMEBREW_TAP_TOKEN" ] && [ -f ../claude-mpm/.env.local ]; then \
		. ../claude-mpm/.env.local; \
	fi; \
	if [ -n "$$HOMEBREW_TAP_TOKEN" ]; then \
		echo "$(BLUE)Updating Homebrew formula (non-blocking)...$(NC)"; \
		HOMEBREW_TAP_TOKEN="$$HOMEBREW_TAP_TOKEN" ./scripts/wait_and_update_homebrew.sh $$NEW_VERSION || \
			echo "$(YELLOW)⚠ Homebrew update failed (non-blocking)$(NC)"; \
	else \
		echo "$(YELLOW)⚠ HOMEBREW_TAP_TOKEN not set - skipping Homebrew update$(NC)"; \
		echo "$(YELLOW)  Set in .env.local or export HOMEBREW_TAP_TOKEN$(NC)"; \
	fi; \
	echo "$(GREEN)═══════════════════════════════════════════════════$(NC)"; \
	echo "$(GREEN)  ✓ Published gworkspace-mcp $$NEW_VERSION$(NC)"; \
	echo "$(GREEN)  ✓ PyPI + GitHub Release + Homebrew$(NC)"; \
	echo "$(GREEN)═══════════════════════════════════════════════════$(NC)"

publish-minor: ## Bump minor version, build, publish to PyPI, tag, and push
	@echo "$(BLUE)═══════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  Publishing Minor Release$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════$(NC)"
	@$(MAKE) pre-publish
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	MINOR=$$(echo $$CURRENT | cut -d. -f2); \
	NEW_MINOR=$$((MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	echo "$(YELLOW)Version: $$CURRENT → $$NEW_VERSION$(NC)"; \
	echo "$$NEW_VERSION" > VERSION; \
	$(MAKE) sync-versions; \
	echo "$(GREEN)✓ Version bumped$(NC)"; \
	git add VERSION src/gworkspace_mcp/VERSION pyproject.toml src/gworkspace_mcp/__version__.py; \
	git commit -m "chore: bump version to $$NEW_VERSION"; \
	echo "$(GREEN)✓ Committed$(NC)"; \
	git tag "v$$NEW_VERSION"; \
	echo "$(GREEN)✓ Tagged v$$NEW_VERSION$(NC)"; \
	git push && git push --tags; \
	echo "$(GREEN)✓ Pushed to origin$(NC)"; \
	rm -rf dist/; \
	$(MAKE) build; \
	echo "$(GREEN)✓ Built package$(NC)"; \
	if [ -f .env.local ]; then \
		. .env.local && UV_PUBLISH_TOKEN="$$PYPI_TOKEN" $(PYTHON) -m twine upload dist/*; \
		echo "$(GREEN)✓ Published to PyPI$(NC)"; \
	else \
		echo "$(RED)✗ .env.local not found - set PYPI_TOKEN$(NC)"; \
		exit 1; \
	fi; \
	if command -v gh >/dev/null 2>&1; then \
		gh release create "v$$NEW_VERSION" \
			--title "v$$NEW_VERSION" \
			--generate-notes \
			dist/* || echo "$(YELLOW)⚠ GitHub CLI not available - skipping release$(NC)"; \
		echo "$(GREEN)✓ GitHub Release created$(NC)"; \
	else \
		echo "$(YELLOW)⚠ GitHub CLI not available - skipping release$(NC)"; \
	fi; \
	if [ -f .env.local ]; then \
		. .env.local; \
	fi; \
	if [ -z "$$HOMEBREW_TAP_TOKEN" ] && [ -f ../claude-mpm/.env.local ]; then \
		. ../claude-mpm/.env.local; \
	fi; \
	if [ -n "$$HOMEBREW_TAP_TOKEN" ]; then \
		echo "$(BLUE)Updating Homebrew formula (non-blocking)...$(NC)"; \
		HOMEBREW_TAP_TOKEN="$$HOMEBREW_TAP_TOKEN" ./scripts/wait_and_update_homebrew.sh $$NEW_VERSION || \
			echo "$(YELLOW)⚠ Homebrew update failed (non-blocking)$(NC)"; \
	else \
		echo "$(YELLOW)⚠ HOMEBREW_TAP_TOKEN not set - skipping Homebrew update$(NC)"; \
		echo "$(YELLOW)  Set in .env.local or export HOMEBREW_TAP_TOKEN$(NC)"; \
	fi; \
	echo "$(GREEN)═══════════════════════════════════════════════════$(NC)"; \
	echo "$(GREEN)  ✓ Published gworkspace-mcp $$NEW_VERSION$(NC)"; \
	echo "$(GREEN)  ✓ PyPI + GitHub Release + Homebrew$(NC)"; \
	echo "$(GREEN)═══════════════════════════════════════════════════$(NC)"

publish-major: ## Bump major version, build, publish to PyPI, tag, and push
	@echo "$(BLUE)═══════════════════════════════════════════════════$(NC)"
	@echo "$(BLUE)  Publishing Major Release$(NC)"
	@echo "$(BLUE)═══════════════════════════════════════════════════$(NC)"
	@$(MAKE) pre-publish
	@CURRENT=$$(cat VERSION); \
	MAJOR=$$(echo $$CURRENT | cut -d. -f1); \
	NEW_MAJOR=$$((MAJOR + 1)); \
	NEW_VERSION="$$NEW_MAJOR.0.0"; \
	echo "$(YELLOW)Version: $$CURRENT → $$NEW_VERSION$(NC)"; \
	echo "$$NEW_VERSION" > VERSION; \
	$(MAKE) sync-versions; \
	echo "$(GREEN)✓ Version bumped$(NC)"; \
	git add VERSION src/gworkspace_mcp/VERSION pyproject.toml src/gworkspace_mcp/__version__.py; \
	git commit -m "chore: bump version to $$NEW_VERSION"; \
	echo "$(GREEN)✓ Committed$(NC)"; \
	git tag "v$$NEW_VERSION"; \
	echo "$(GREEN)✓ Tagged v$$NEW_VERSION$(NC)"; \
	git push && git push --tags; \
	echo "$(GREEN)✓ Pushed to origin$(NC)"; \
	rm -rf dist/; \
	$(MAKE) build; \
	echo "$(GREEN)✓ Built package$(NC)"; \
	if [ -f .env.local ]; then \
		. .env.local && UV_PUBLISH_TOKEN="$$PYPI_TOKEN" $(PYTHON) -m twine upload dist/*; \
		echo "$(GREEN)✓ Published to PyPI$(NC)"; \
	else \
		echo "$(RED)✗ .env.local not found - set PYPI_TOKEN$(NC)"; \
		exit 1; \
	fi; \
	if command -v gh >/dev/null 2>&1; then \
		gh release create "v$$NEW_VERSION" \
			--title "v$$NEW_VERSION" \
			--generate-notes \
			dist/* || echo "$(YELLOW)⚠ GitHub CLI not available - skipping release$(NC)"; \
		echo "$(GREEN)✓ GitHub Release created$(NC)"; \
	else \
		echo "$(YELLOW)⚠ GitHub CLI not available - skipping release$(NC)"; \
	fi; \
	if [ -f .env.local ]; then \
		. .env.local; \
	fi; \
	if [ -z "$$HOMEBREW_TAP_TOKEN" ] && [ -f ../claude-mpm/.env.local ]; then \
		. ../claude-mpm/.env.local; \
	fi; \
	if [ -n "$$HOMEBREW_TAP_TOKEN" ]; then \
		echo "$(BLUE)Updating Homebrew formula (non-blocking)...$(NC)"; \
		HOMEBREW_TAP_TOKEN="$$HOMEBREW_TAP_TOKEN" ./scripts/wait_and_update_homebrew.sh $$NEW_VERSION || \
			echo "$(YELLOW)⚠ Homebrew update failed (non-blocking)$(NC)"; \
	else \
		echo "$(YELLOW)⚠ HOMEBREW_TAP_TOKEN not set - skipping Homebrew update$(NC)"; \
		echo "$(YELLOW)  Set in .env.local or export HOMEBREW_TAP_TOKEN$(NC)"; \
	fi; \
	echo "$(GREEN)═══════════════════════════════════════════════════$(NC)"; \
	echo "$(GREEN)  ✓ Published gworkspace-mcp $$NEW_VERSION$(NC)"; \
	echo "$(GREEN)  ✓ PyPI + GitHub Release + Homebrew$(NC)"; \
	echo "$(GREEN)═══════════════════════════════════════════════════$(NC)"

publish-only: ## Publish current version to PyPI (no version bump)
	@echo "$(BLUE)Publishing current version to PyPI...$(NC)"
	@rm -rf dist/
	@$(MAKE) build
	@if [ -f .env.local ]; then \
		. .env.local && UV_PUBLISH_TOKEN="$$PYPI_TOKEN" $(PYTHON) -m twine upload dist/*; \
		echo "$(GREEN)✓ Published to PyPI$(NC)"; \
	else \
		echo "$(RED)✗ .env.local not found - set PYPI_TOKEN$(NC)"; \
		exit 1; \
	fi

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
	@echo "$(YELLOW)Checking environment configuration...$(NC)"
	@if [ ! -f .env.local ]; then \
		echo "$(RED)✗ .env.local not found$(NC)"; \
		echo "$(YELLOW)  Copy .env.local.example and configure tokens$(NC)"; \
		exit 1; \
	else \
		echo "$(GREEN)✓ .env.local found$(NC)"; \
	fi
	@echo ""
	@echo "$(GREEN)============================================$(NC)"
	@echo "$(GREEN)Pre-publish checks PASSED!$(NC)"
	@echo "$(GREEN)============================================$(NC)"

# ============================================================================
# Homebrew Operations
# ============================================================================

.PHONY: homebrew-update homebrew-test homebrew-dry-run

homebrew-update: ## Update Homebrew formula with current version
	@echo "$(BLUE)Updating Homebrew formula...$(NC)"
	@VERSION=$$(cat VERSION); \
	if [ -f .env.local ]; then \
		. .env.local; \
	fi; \
	if [ -z "$$HOMEBREW_TAP_TOKEN" ] && [ -f ../claude-mpm/.env.local ]; then \
		. ../claude-mpm/.env.local; \
	fi; \
	if [ -z "$$HOMEBREW_TAP_TOKEN" ]; then \
		echo "$(RED)✗ HOMEBREW_TAP_TOKEN not set$(NC)"; \
		echo "$(YELLOW)  Set in .env.local or ../claude-mpm/.env.local$(NC)"; \
		exit 1; \
	fi; \
	HOMEBREW_TAP_TOKEN="$$HOMEBREW_TAP_TOKEN" python3 scripts/update_homebrew.py --version $$VERSION --verbose

homebrew-dry-run: ## Test Homebrew formula update (dry-run)
	@echo "$(BLUE)Testing Homebrew formula update (dry-run)...$(NC)"
	@VERSION=$$(cat VERSION); \
	python3 scripts/update_homebrew.py --version $$VERSION --dry-run --verbose

homebrew-test: ## Test Homebrew formula locally
	@echo "$(BLUE)Testing Homebrew formula locally...$(NC)"
	@if ! command -v brew >/dev/null 2>&1; then \
		echo "$(RED)✗ Homebrew not installed$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)Instructions for local testing:$(NC)"
	@echo "  brew tap masapasa/gworkspace-mcp"
	@echo "  brew install --build-from-source gworkspace-mcp"
	@echo "$(GREEN)Run the above commands to test locally$(NC)"

# ============================================================================
# Legacy Targets (Maintained for Compatibility)
# ============================================================================

# Legacy target maintained for compatibility
publish-pypi: pre-publish build ## Legacy target - use 'publish' instead
	@echo "$(YELLOW)⚠ 'publish-pypi' is deprecated - use 'make publish' instead$(NC)"
	@$(MAKE) publish-only
