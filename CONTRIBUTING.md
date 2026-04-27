# Contributing to Yankit

First off, thank you for considering contributing to Yankit! It's people like you that make Yankit such a great tool.

## How Can I Contribute?

### Reporting Bugs
- Use the **Bug Report** template when opening an issue.
- Describe the steps to reproduce the issue.
- Include details about your environment (OS, Python version, Terminal emulator).

### Suggesting Enhancements
- Use the **Feature Request** template.
- Explain why this enhancement would be useful to most users.

### Pull Requests
1. Fork the repository and create your branch from `main`.
2. If you've added code that should be tested, add tests.
3. Ensure the test suite passes and the code follows the style guidelines (we use `ruff`).
4. If your PR is related to an open issue, please tag it in the description (e.g., `Closes #123`).
5. Open the PR and wait for review!

## Development Setup

We use `uv` for dependency management.

```bash
# Clone the repo
git clone https://github.com/oktaysabak/yankit.git
cd yankit

# Install dependencies
uv sync

# Run yankit in development mode
uv run yankit
```

## Style Guidelines
We use `ruff` for linting and formatting. Please run these before committing:
```bash
uv run ruff check --fix
uv run ruff format
```

Thank you for your contribution!
