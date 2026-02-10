# Release Process

This guide documents how releases are created for google-workspace-mcp.

## Version Numbering

We follow [Semantic Versioning](https://semver.org/) (SemVer):

```
MAJOR.MINOR.PATCH

Example: 1.2.3
```

| Increment | When to Use |
|-----------|-------------|
| MAJOR | Breaking changes, incompatible API changes |
| MINOR | New features, backwards compatible |
| PATCH | Bug fixes, backwards compatible |

## Version Files

Version is stored in multiple locations (kept in sync):

| File | Purpose |
|------|---------|
| `VERSION` | Root version file |
| `src/google_workspace_mcp/__version__.py` | Python package version |
| `pyproject.toml` | Package metadata |

## Release Checklist

### Pre-Release

- [ ] All tests pass (`pytest`)
- [ ] Code quality checks pass (`ruff check`, `mypy`)
- [ ] CHANGELOG.md updated
- [ ] Documentation updated if needed
- [ ] Version numbers synchronized

### Release Steps

1. **Update version numbers**:
   ```bash
   # Update VERSION file
   echo "1.0.0" > VERSION

   # Update __version__.py
   # Update pyproject.toml
   ```

2. **Update CHANGELOG.md**:
   ```markdown
   ## [1.0.0] - 2024-01-15

   ### Added
   - New feature X

   ### Fixed
   - Bug fix Y

   ### Changed
   - Updated Z
   ```

3. **Commit version changes**:
   ```bash
   git add VERSION CHANGELOG.md pyproject.toml src/google_workspace_mcp/__version__.py
   git commit -m "chore: bump version to 1.0.0"
   ```

4. **Create git tag**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   git push origin main
   ```

5. **Build distribution**:
   ```bash
   # Clean previous builds
   rm -rf dist/ build/ *.egg-info

   # Build
   python -m build
   # or
   uv build
   ```

6. **Publish to PyPI**:
   ```bash
   # Upload to PyPI
   twine upload dist/*
   # or
   uv publish
   ```

7. **Create GitHub release**:
   ```bash
   gh release create v1.0.0 \
     --title "Release 1.0.0" \
     --notes "See CHANGELOG.md for details"
   ```

### Post-Release

- [ ] Verify package on PyPI
- [ ] Test installation in clean environment
- [ ] Update documentation if needed

## CHANGELOG Format

Follow [Keep a Changelog](https://keepachangelog.com/):

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2024-01-15

### Added
- New feature description

### Changed
- Change description

### Deprecated
- Deprecated feature description

### Removed
- Removed feature description

### Fixed
- Bug fix description

### Security
- Security fix description
```

## PyPI Publishing

### Prerequisites

1. **PyPI account**: Create at [pypi.org](https://pypi.org/)

2. **API token**: Create at PyPI account settings

3. **Configure credentials**:
   ```bash
   # Create ~/.pypirc
   cat > ~/.pypirc << 'EOF'
   [pypi]
   username = __token__
   password = pypi-YOUR_API_TOKEN_HERE
   EOF

   # Secure the file
   chmod 600 ~/.pypirc
   ```

### Build and Upload

```bash
# Clean build
rm -rf dist/ build/ *.egg-info

# Build
python -m build

# Verify build
twine check dist/*

# Upload to TestPyPI first (recommended)
twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ google-workspace-mcp

# Upload to PyPI
twine upload dist/*
```

### Using uv

```bash
# Build
uv build

# Publish (requires UV_PUBLISH_TOKEN)
export UV_PUBLISH_TOKEN="pypi-YOUR_TOKEN"
uv publish
```

## GitHub Actions

Releases can be automated with GitHub Actions:

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install build twine

      - name: Build
        run: python -m build

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: twine upload dist/*
```

## Hotfix Process

For urgent bug fixes:

1. Create hotfix branch from tag:
   ```bash
   git checkout -b hotfix/1.0.1 v1.0.0
   ```

2. Apply fix and commit

3. Update version to patch level:
   ```bash
   echo "1.0.1" > VERSION
   ```

4. Tag and release:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```

5. Merge hotfix to main:
   ```bash
   git checkout main
   git merge hotfix/1.0.1
   git push origin main
   ```

## Troubleshooting

### Upload fails with "File already exists"

PyPI doesn't allow overwriting existing versions. Increment the version number.

### Package not found after upload

PyPI index updates may take a few minutes. Wait and retry:

```bash
pip install --no-cache-dir google-workspace-mcp
```

### Wrong files in distribution

Check `pyproject.toml` includes/excludes:

```toml
[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
"*" = ["VERSION"]
```

## Related Documentation

- [Contributing Guide](contributing.md)
- [Testing Guide](testing.md)
