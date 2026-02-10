# PyPI Publishing Setup Research

**Source Project**: `/Users/masa/Projects/claude-mpm`
**Target Project**: `/Users/masa/Projects/google-workspace-mcp`
**Research Date**: 2026-02-10

---

## Executive Summary

The claude-mpm project uses a comprehensive PyPI publishing workflow with:
- **API Key Storage**: `~/.pypirc` file with PyPI token
- **Makefile Targets**: Extensive release automation (30+ targets)
- **Version Management**: VERSION file + BUILD_NUMBER file + commitizen
- **Release Scripts**: Automated release script with quality gates

---

## 1. PyPI Configuration

### API Key Storage Location

**Primary Method**: `~/.pypirc` file

```ini
# ~/.pypirc (home directory, NOT in project)
[pypi]
username = __token__
password = pypi-AgEI...your-token-here...
```

**File Permissions**: `chmod 600 ~/.pypirc`

**Alternative Method (legacy)**: `.env.local` in project root
```bash
# .env.local (must be gitignored)
PYPI_API_KEY=pypi-AgEI...your-token-here...
```

### Script: `scripts/publish_to_pypi.sh`

Key features:
- Reads token from `~/.pypirc`
- Extracts password field and exports as `UV_PUBLISH_TOKEN`
- Validates VERSION file and dist/ files exist
- Uses `uv publish` or `twine upload`
- Includes Homebrew tap update after publish

**Relevant excerpt**:
```bash
# Extract PyPI token from ~/.pypirc for uv publish
PYPI_TOKEN=$(grep '^password' ~/.pypirc | head -1 | cut -d'=' -f2 | tr -d ' ')
export UV_PUBLISH_TOKEN="$PYPI_TOKEN"

# Upload using uv
uv publish "$WHEEL_FILE" "$TAR_FILE"
```

---

## 2. Makefile Targets

### Complete Publish-Related Targets

**From `/Users/masa/Projects/claude-mpm/Makefile`**:

```makefile
# ============================================================================
# Publishing Workflow
# ============================================================================

# Publish to PyPI using .env.local credentials
publish-pypi: ## Publish package to PyPI using credentials from .env.local
	@./scripts/publish_to_pypi.sh

# Update Homebrew tap formula (non-blocking)
update-homebrew-tap: ## Update Homebrew tap formula after PyPI publish
	@VERSION=$$(cat VERSION); \
	./scripts/update_homebrew_tap.sh "$$VERSION" --auto-push

# Publish release to all channels
release-publish: ## Publish release to PyPI, npm, Homebrew, and GitHub
	# Sync repos -> PyPI -> Homebrew -> npm -> GitHub Release

# Publish to TestPyPI for testing
release-test-pypi: release-build ## Publish to TestPyPI for testing
	@twine upload --repository testpypi dist/*
```

### Build Targets

```makefile
# Development build (fast, no checks)
build-dev: ## Development build (fast, no checks)
	@rm -rf $(DIST_DIR) $(BUILD_DIR)
	@$(PYTHON) -m build --wheel $(BUILD_FLAGS)

# Production build (with all checks)
build-prod: quality ## Production build (with all checks)
	@$(MAKE) build-metadata
	@rm -rf $(DIST_DIR) $(BUILD_DIR) *.egg-info
	@uv build $(BUILD_FLAGS)
	@$(MAKE) build-info-json

# Safe release build (explicit quality gate)
safe-release-build: ## Build release with mandatory quality checks
	@$(MAKE) pre-publish
	@$(PYTHON) scripts/increment_build.py --all-changes
	@$(MAKE) build-metadata
	@rm -rf $(DIST_DIR) $(BUILD_DIR) *.egg-info
	@uv build $(BUILD_FLAGS)
```

### Release Targets (Commitizen-based)

```makefile
# Release prerequisites check
release-check: ## Check if environment is ready for release
	# Checks: git, python, cz, gh CLI, clean working directory, main branch

# Run tests before release
release-test: ## Run test suite before release

# Build the package (with quality checks)
release-build: pre-publish ## Build Python package for release
	@python scripts/increment_build.py --all-changes
	@rm -rf dist/ build/ *.egg-info
	@uv build

# Patch release (bug fixes)
release-patch: release-check release-test ## Create a patch release
	@cz bump --increment PATCH
	@$(MAKE) release-build

# Minor release (new features)
release-minor: release-check release-test ## Create a minor release
	@cz bump --increment MINOR
	@$(MAKE) release-build

# Major release (breaking changes)
release-major: release-check release-test ## Create a major release
	@cz bump --increment MAJOR
	@$(MAKE) release-build
```

### Automated Release Targets (Alternative to Commitizen)

```makefile
# Automated patch release
auto-patch: ## Automated patch release (alternative to commitizen)
	python scripts/automated_release.py --patch

# Automated minor release
auto-minor: ## Automated minor release
	python scripts/automated_release.py --minor

# Automated major release
auto-major: ## Automated major release
	python scripts/automated_release.py --major

# Automated build-only release
auto-build: ## Automated build-only release (no version bump)
	python scripts/automated_release.py --build

# Sync version files
sync-versions: ## Sync version between root and package VERSION files
	@VERSION=$$(cat VERSION); \
	echo "$$VERSION" > src/claude_mpm/VERSION;
```

### Pre-Publish Quality Gates

```makefile
# Pre-publish quality gate
pre-publish: clean-pre-publish ## Run cleanup and all quality checks before publishing
	# Step 1/5: Check working directory clean
	# Step 2/5: Run all linters (lint-all)
	# Step 3/5: Run tests
	# Step 4/5: Check for common issues (debug prints, TODOs)
	# Step 5/6: Validate version consistency
	# Step 6/6: Check PM behavioral compliance
```

---

## 3. Semantic Versioning

### Version File Structure

```
/Users/masa/Projects/claude-mpm/
├── VERSION                           # "5.7.25"
├── BUILD_NUMBER                      # "601"
├── src/claude_mpm/VERSION            # "5.7.25" (synced)
├── package.json                      # "version": "5.7.25"
└── pyproject.toml                    # version = "5.7.25"
                                      # [tool.commitizen] version = "5.7.25"
```

### Version Management Tools

**1. Commitizen** (`cz` CLI)
- Configured in `pyproject.toml`:
```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "5.7.25"
version_files = [ "VERSION", "src/claude_mpm/VERSION", "package.json:version"]
tag_format = "v$version"
update_changelog_on_bump = true
changelog_incremental = true
```

**2. Custom Script**: `scripts/manage_version.py`
```bash
./scripts/manage_version.py show          # Display current version
./scripts/manage_version.py increment patch  # Bump patch version
./scripts/manage_version.py increment minor  # Bump minor version
./scripts/manage_version.py build           # Increment build only
```

**3. Automated Release Script**: `tools/dev/automated_release.py`
```bash
python tools/dev/automated_release.py --patch           # Patch release
python tools/dev/automated_release.py --minor           # Minor release
python tools/dev/automated_release.py --major           # Major release
python tools/dev/automated_release.py --build           # Build-only
python tools/dev/automated_release.py --patch --yes     # Auto-confirm
python tools/dev/automated_release.py --patch --skip-agent-sync
```

### Build Number Tracking

**Script**: `scripts/increment_build.py`

Features:
- Only increments on actual code changes (not docs/config)
- Uses git diff to detect changes
- Code files: `src/**/*.py`, `scripts/**/*.sh`, `scripts/**/*.py`
- Excluded: `*.md`, `docs/`, `agents/templates/*.json`

```bash
python scripts/increment_build.py              # Staged files only
python scripts/increment_build.py --all-changes  # All changes
python scripts/increment_build.py --check-only   # Report only
python scripts/increment_build.py --force        # Force increment
```

---

## 4. Release Workflow

### Complete Release Process

From `docs/developer/publishing-guide.md`:

```bash
# 1. Ensure working directory is clean
git status

# 2. Run pre-publish cleanup and quality checks
make pre-publish

# 3. Bump version
./scripts/manage_version.py bump patch
# Or: make auto-patch
# Or: make increment-build

# 4. Update CHANGELOG.md (manually add release notes)

# 5. Commit version changes
git add VERSION CHANGELOG.md
git commit -m "chore: bump version to X.Y.Z"

# 6. Build distribution files with quality checks
make safe-release-build

# 7. Verify build artifacts
ls -lh dist/

# 8. Publish to PyPI
make publish-pypi

# 9. Verify publication
# Visit https://pypi.org/project/claude-mpm/

# 10. Test installation in clean environment
python -m venv test_env
source test_env/bin/activate
pip install --upgrade claude-mpm
claude-mpm --version
deactivate && rm -rf test_env

# 11. Create git tag
git tag vX.Y.Z
git push origin vX.Y.Z

# 12. Create GitHub release
gh release create vX.Y.Z \
    --title "Release X.Y.Z" \
    --notes "$(cat CHANGELOG.md | head -n 50)"

# 13. Push changes
git push origin main
```

### Quick Automated Release

```bash
# Option 1: Commitizen-based
make release-patch
make release-publish

# Option 2: Fully automated
make auto-patch  # Does everything in one command
```

---

## 5. Git Tagging

### Tag Format

```bash
# Tag format: v{version}
git tag v5.7.25
git push origin v5.7.25
git push origin --tags  # All tags
```

### Commitizen Configuration

```toml
[tool.commitizen]
tag_format = "v$version"
```

---

## 6. Changelog Generation

### Commitizen Auto-Update

```toml
[tool.commitizen]
update_changelog_on_bump = true
changelog_incremental = true
```

### CHANGELOG.md Format

```markdown
## [Unreleased]

### Added
### Changed
### Fixed
### Documentation
### Tests

## [5.7.25] - 2026-02-10

### Added
- Feature description

### Fixed
- Bug fix description
```

---

## 7. Verification Script

**Script**: `scripts/verify_publish_setup.sh`

Checks performed:
1. Project root (pyproject.toml exists)
2. `.env.local` file exists (or `~/.pypirc`)
3. File permissions (600)
4. `.gitignore` includes `.env.local`
5. API key format (starts with `pypi-`)
6. API key length (200+ chars typical)
7. VERSION file exists
8. Distribution files exist (dist/*.whl, dist/*.tar.gz)
9. Required tools: `uv`, `git`, `python`
10. Publish script exists and is executable

---

## 8. Replication Recommendations for google-workspace-mcp

### Minimum Required Files

1. **VERSION** - Root version file
2. **BUILD_NUMBER** - Build tracking
3. **src/google_workspace_mcp/VERSION** - Package version (synced)
4. **scripts/publish_to_pypi.sh** - Publishing script
5. **Makefile** - Build/release targets

### Recommended Makefile Targets

```makefile
# Core targets
publish-pypi        # Publish to PyPI
release-build       # Build with quality checks
release-patch       # Patch release
release-minor       # Minor release
pre-publish         # Quality gate
increment-build     # Bump build number
sync-versions       # Sync VERSION files
```

### PyPI Credential Setup

```bash
# Create ~/.pypirc if not exists
cat > ~/.pypirc << 'EOF'
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE
EOF
chmod 600 ~/.pypirc
```

### pyproject.toml Configuration

```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "0.1.0"
version_files = ["VERSION", "src/google_workspace_mcp/VERSION"]
tag_format = "v$version"
update_changelog_on_bump = true
changelog_incremental = true
```

---

## 9. Key Differences for google-workspace-mcp

| Aspect | claude-mpm | google-workspace-mcp |
|--------|------------|---------------------|
| Package name | claude-mpm | google-workspace-mcp |
| Entry point | claude_mpm.cli:main | workspace_mcp.cli:main |
| Version path | src/claude_mpm/VERSION | src/google_workspace_mcp/VERSION |
| Homebrew tap | Yes (complex) | No (simpler) |
| npm publish | Yes | No |
| Agent repo sync | Yes | No |

---

## 10. Files to Copy/Adapt

### Direct Copy (with path updates)
- `scripts/publish_to_pypi.sh` (update package name)
- `scripts/increment_build.py` (update paths)
- `scripts/manage_version.py` (update paths)
- `scripts/verify_publish_setup.sh` (update package name)

### Simplified Version Needed
- `tools/dev/automated_release.py` (remove agent sync, npm, homebrew)

### New Files to Create
- `VERSION` (initial: "0.1.0")
- `BUILD_NUMBER` (initial: "1")
- `CHANGELOG.md` (standard format)

### Makefile Targets to Add
- Core release targets from claude-mpm
- Remove: Homebrew, npm, agent sync, PM behavioral tests

---

## Research Complete

This document provides all necessary information to replicate the PyPI publishing setup from claude-mpm to google-workspace-mcp. The key insight is that claude-mpm uses a multi-layered approach:

1. **Simple case**: `~/.pypirc` + `uv publish`
2. **Automated case**: `tools/dev/automated_release.py`
3. **Quality gates**: `make pre-publish` before any release

For google-workspace-mcp, start with the simple case and add automation as needed.
