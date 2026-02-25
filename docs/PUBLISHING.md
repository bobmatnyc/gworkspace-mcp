# Publishing Guide for gworkspace-mcp

This document describes the unified publishing system for gworkspace-mcp, which automates publishing to PyPI, GitHub Releases, and Homebrew with a single command.

## Overview

The publishing system is based on successful patterns from mcp-vector-search and provides:

- **Single-command publishing** to all platforms
- **Automatic version management** across all files
- **Non-blocking Homebrew updates** with retry logic
- **Environment-based configuration** for security
- **Comprehensive error handling** and rollback

## Quick Start

1. **Set up environment** (one-time setup):
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your API tokens
   ```

2. **Publish a patch release**:
   ```bash
   make publish
   ```

That's it! This single command will:
- Bump the patch version (0.1.25 → 0.1.26)
- Update all version files
- Build and publish to PyPI
- Create GitHub release with auto-generated notes
- Update Homebrew formula (non-blocking)

## Environment Setup

### Required API Tokens

Copy `.env.local.example` to `.env.local` and configure:

```bash
# PyPI API Token
PYPI_TOKEN=pypi-your-token-here

# GitHub Personal Access Token
GITHUB_TOKEN=ghp_your-token-here

# Homebrew Tap Token (usually same as GitHub)
HOMEBREW_TAP_TOKEN=gho_your-token-here
```

### Getting API Tokens

1. **PyPI Token**: https://pypi.org/manage/account/token/
   - Create token with "Upload packages" scope
   - Copy the full token including `pypi-` prefix

2. **GitHub Token**: https://github.com/settings/tokens
   - Needs: `repo`, `workflow`, `write:packages` scopes
   - Copy the full token

3. **Homebrew Tap Token**: Usually same as GitHub token
   - For updating the shared bobmatnyc/homebrew-tools tap

### Security Notes

- `.env.local` is in `.gitignore` and never committed
- Store tokens securely in your password manager
- Rotate tokens regularly for security

## Publishing Commands

### Main Commands

| Command | Description | Version Change |
|---------|-------------|----------------|
| `make publish` | Patch release + full publish | 0.1.25 → 0.1.26 |
| `make publish-minor` | Minor release + full publish | 0.1.25 → 0.2.0 |
| `make publish-major` | Major release + full publish | 0.1.25 → 1.0.0 |
| `make publish-only` | Publish current version (no bump) | No change |

### Homebrew Operations

| Command | Description |
|---------|-------------|
| `make homebrew-dry-run` | Test Homebrew update without changes |
| `make homebrew-update` | Update Homebrew formula manually |
| `make homebrew-test` | Local Homebrew installation test |

## Publishing Workflow

### 1. Full Release (Recommended)

```bash
# Ensure working directory is clean
git status

# Run tests and checks
make test lint

# Publish patch release
make publish
```

### 2. Minor/Major Releases

```bash
# For breaking changes or new features
make publish-minor

# For major version milestones
make publish-major
```

### 3. Manual Steps (if needed)

```bash
# Just update version without publishing
make bump-patch
make sync-versions

# Build and test locally
make build
make test

# Publish to PyPI only
make publish-only

# Update Homebrew separately
make homebrew-update
```

## Version Management

### Single Source of Truth

Version is stored in `VERSION` file and automatically synced to:
- `pyproject.toml` - Package metadata
- `src/gworkspace_mcp/VERSION` - Runtime version file
- `src/gworkspace_mcp/__version__.py` - Python module version

### Version Bumping

The system uses semantic versioning:
- **Patch** (0.1.25 → 0.1.26): Bug fixes, minor improvements
- **Minor** (0.1.25 → 0.2.0): New features, backward compatible
- **Major** (0.1.25 → 1.0.0): Breaking changes

## Platform Details

### PyPI Publishing

- Uses `uv publish` if available, falls back to `twine`
- Automatically builds wheel and source distribution
- Includes package verification before upload
- Provides direct link to published package

### GitHub Releases

- Creates git tag with version number
- Generates release notes from recent commits
- Uploads distribution files as release assets
- Requires `gh` CLI tool for automatic creation

### Homebrew Integration

- **Non-blocking**: Won't fail the release if Homebrew update fails
- **Retry logic**: Waits for PyPI availability with exponential backoff
- **Auto-updates**: Fetches SHA256 from PyPI automatically
- **Manual fallback**: Provides instructions if automation fails

## Troubleshooting

### Common Issues

1. **"Working directory not clean"**
   ```bash
   git status
   git add .
   git commit -m "fix: prepare for release"
   ```

2. **"PYPI_TOKEN not found"**
   ```bash
   cp .env.local.example .env.local
   # Edit .env.local with your PyPI token
   ```

3. **"GitHub CLI not available"**
   ```bash
   # Install GitHub CLI
   brew install gh
   # Or download from https://cli.github.com/
   ```

4. **Homebrew update failed (non-blocking)**
   ```bash
   # Check PyPI availability first
   curl -s https://pypi.org/pypi/gworkspace-mcp/0.1.26/json

   # Manual Homebrew update
   make homebrew-update
   ```

### Manual Recovery

If something goes wrong during publishing:

```bash
# Check git status
git status
git log --oneline -5

# Reset version if needed
git reset --hard HEAD~1

# Or manually fix version files
echo "0.1.25" > VERSION
make sync-versions
```

### Debug Mode

```bash
# Test Homebrew update without changes
make homebrew-dry-run

# Verbose output for debugging
python3 scripts/update_homebrew.py --version 0.1.26 --dry-run --verbose
```

## Architecture

### File Structure

```
gworkspace-mcp/
├── .env.local.example          # Environment template
├── .env.local                  # Local environment (gitignored)
├── VERSION                     # Single source of truth
├── Makefile                    # Publishing commands
└── scripts/
    ├── update_homebrew.py      # Homebrew formula updater
    ├── wait_and_update_homebrew.sh  # PyPI wait + Homebrew update
    └── publish_to_pypi.sh      # PyPI publishing script
```

### Error Handling Strategy

1. **Pre-flight checks**: Validate environment and dependencies
2. **Atomic operations**: Each step completes fully or rolls back
3. **Non-blocking Homebrew**: PyPI and GitHub succeed even if Homebrew fails
4. **Comprehensive logging**: Clear success/failure reporting
5. **Manual fallbacks**: Instructions provided for manual recovery

### Dependencies

- **Required**: `git`, `python3`, basic build tools
- **Recommended**: `uv` (faster builds), `gh` (GitHub releases)
- **Optional**: `brew` (for local Homebrew testing)

## Best Practices

### Before Publishing

1. **Test thoroughly**: Run full test suite
2. **Update CHANGELOG**: Document what's changing
3. **Clean working directory**: Commit all changes
4. **Verify environment**: Check `.env.local` is configured

### Release Planning

1. **Patch releases**: Bug fixes, documentation, minor improvements
2. **Minor releases**: New features, backward-compatible changes
3. **Major releases**: Breaking changes, major milestones

### Security

1. **Protect tokens**: Never commit `.env.local` to git
2. **Rotate regularly**: Update API tokens periodically
3. **Minimal scope**: Use tokens with minimum required permissions
4. **Monitor usage**: Watch for unusual activity on your packages

## Integration

This publishing system integrates with:

- **CI/CD pipelines**: Can be automated with GitHub Actions
- **Development workflow**: Follows git-flow patterns
- **Version management**: Semantic versioning standards
- **Package management**: Standard Python packaging tools

For more advanced automation, consider setting up GitHub Actions to trigger releases on tag creation or manual workflow dispatch.

## Support

If you encounter issues with the publishing system:

1. Check this documentation first
2. Look at the Makefile targets for debugging commands
3. Run commands with verbose flags for detailed output
4. Check the scripts/ directory for implementation details

The system is designed to be robust and recoverable, with manual fallback options for every automated step.