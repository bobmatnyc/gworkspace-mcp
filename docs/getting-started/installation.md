# Installation

This guide covers installing gworkspace-mcp on your system.

## Quick Install

### Using pip

```bash
pip install gworkspace-mcp
```

### Using uv (recommended)

[uv](https://github.com/astral-sh/uv) is a fast Python package manager:

```bash
uv pip install gworkspace-mcp
```

### Using pipx (isolated environment)

For CLI tools, [pipx](https://pipx.pypa.io/) provides isolated installs:

```bash
pipx install gworkspace-mcp
```

## Verify Installation

After installation, verify the CLI is available:

```bash
workspace --version
```

Expected output:
```
gworkspace-mcp version 0.1.0
```

## Development Installation

For contributing or modifying the code:

```bash
# Clone the repository
git clone https://github.com/masapasa/gworkspace-mcp.git
cd gworkspace-mcp

# Install with development dependencies
pip install -e ".[dev]"
```

Development dependencies include:
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-asyncio` - Async test support
- `ruff` - Linting and formatting
- `mypy` - Type checking
- `pre-commit` - Git hooks

## System Requirements

### Required

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ |
| Operating System | macOS, Linux, Windows |

### Python Dependencies

These are installed automatically:

| Package | Purpose |
|---------|---------|
| `mcp` | Model Context Protocol SDK |
| `google-auth` | Google authentication |
| `google-auth-oauthlib` | OAuth 2.0 flows |
| `google-api-python-client` | Google API client |
| `httpx` | HTTP client |
| `pydantic` | Data validation |
| `click` | CLI framework |

### Optional Dependencies

For full functionality, install these optional tools:

#### rclone (Drive Sync)

Required for 4 Drive sync tools.

**macOS**:
```bash
brew install rclone
```

**Linux**:
```bash
curl https://rclone.org/install.sh | sudo bash
```

**Windows**:
```powershell
winget install Rclone.Rclone
```

Verify: `rclone version`

#### pandoc (Document Conversion)

Required for `upload_markdown_as_doc`.

**macOS**:
```bash
brew install pandoc
```

**Linux**:
```bash
sudo apt-get install pandoc
```

**Windows**:
```powershell
winget install JohnMacFarlane.Pandoc
```

Verify: `pandoc --version`

#### mermaid-cli (Diagram Rendering)

Required for `render_mermaid_to_doc`.

```bash
npm install -g @mermaid-js/mermaid-cli
```

Verify: `mmdc --version`

## Troubleshooting

### "command not found: workspace"

The CLI is not in your PATH. Solutions:

1. **Check installation location**:
   ```bash
   pip show gworkspace-mcp
   ```

2. **Add to PATH** (if using pipx):
   ```bash
   pipx ensurepath
   ```

3. **Reinstall with pip**:
   ```bash
   pip uninstall gworkspace-mcp
   pip install gworkspace-mcp
   ```

### Python version errors

Ensure you're using Python 3.10 or higher:

```bash
python --version
```

If you have multiple Python versions, use:

```bash
python3.10 -m pip install gworkspace-mcp
```

### Permission errors on Linux/macOS

Use `--user` flag or a virtual environment:

```bash
pip install --user gworkspace-mcp
```

Or with a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install gworkspace-mcp
```

## Next Steps

After installation:

1. [Set up authentication](authentication.md) - Configure Google OAuth
2. [Quickstart guide](quickstart.md) - Your first API call
3. [Claude Desktop integration](../guides/claude-desktop.md) - Connect to Claude
