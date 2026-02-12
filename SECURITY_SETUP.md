# Security Tool Setup Guide

This guide explains how to set up the security scanning tools used in this project.

## Bandit (Python Security Scanner)

### Installation

```bash
# Using pip
pip install bandit

# Using pipx (recommended for CLI tools)
pipx install bandit

# Using Homebrew (macOS)
brew install bandit
```

### Usage

```bash
# Run Bandit security scanner
./run_bandit.sh
```

### Configuration

Bandit configuration is in `.bandit` (YAML format):
- Excluded directories: test files, git, venv
- Skipped tests: B404, B603, B607 (subprocess is used deliberately)
- Severity threshold: medium
- Confidence threshold: medium

## ShellCheck (Bash Security Linter)

### Installation

```bash
# macOS
brew install shellcheck

# Ubuntu/Debian
sudo apt-get install shellcheck

# Fedora
sudo dnf install shellcheck

# Or download from: https://www.shellcheck.net/
```

### Usage

```bash
# Run ShellCheck on all bash scripts
./run_shellcheck.sh
```

### Configuration

ShellCheck configuration is in `.shellcheckrc`:
- Disabled checks: SC2086 (intentional unquoted variables)
- Enabled: all optional checks
- Shell dialect: bash

## Snyk (Dependency Vulnerability Scanner)

Snyk scans for known vulnerabilities in dependencies. The GitHub Actions workflow includes Snyk scanning, but it requires setup.

### Setup for GitHub Actions

1. **Sign up for Snyk:**
   - Go to https://snyk.io
   - Sign up for a free account (supports open source projects)
   - Link your GitHub account

2. **Get your Snyk API token:**
   - Go to https://app.snyk.io/account
   - Navigate to "General" settings
   - Copy your API token (starts with a UUID)

3. **Add token to GitHub Secrets:**
   - Go to your GitHub repository
   - Navigate to Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `SNYK_TOKEN`
   - Value: Paste your Snyk API token
   - Click "Add secret"

4. **Verify setup:**
   - Push a commit to trigger GitHub Actions
   - Check the "Actions" tab
   - The "snyk-scan" job should now run successfully

### Local Usage (Optional)

```bash
# Install Snyk CLI
npm install -g snyk

# Authenticate
snyk auth

# Test for vulnerabilities
snyk test --file=requirements.txt --package-manager=pip

# Monitor project (sends results to Snyk dashboard)
snyk monitor
```

### Snyk Configuration

The GitHub Actions workflow (`.github/workflows/security.yml`) includes:
- Runs only on pushes to `main` branch
- Uses `snyk/actions/python@master`
- Continues on error (doesn't fail build)
- Requires `SNYK_TOKEN` secret

## GitHub Actions Workflow

All security tools run automatically via `.github/workflows/security.yml`:

### What runs automatically:

**On every push/PR to main:**
- Bandit Python security scanner
- ShellCheck bash linter
- Ruff Python linter
- Security fuzzing tests (`security_tests.sh`)
- Full test harness (`test_exports.sh`)

**On push to main only:**
- Snyk vulnerability scanning (requires `SNYK_TOKEN`)

### Viewing Results

1. Go to your repository on GitHub
2. Click the "Actions" tab
3. Select a workflow run to see detailed results
4. Click on individual jobs to see security scan output

### Badge Status

Add a workflow status badge to your README:

```markdown
![Security Checks](https://github.com/YOUR_USERNAME/YOUR_REPO/actions/workflows/security.yml/badge.svg)
```

## Running All Checks Locally

```bash
# Install all tools (macOS)
brew install shellcheck
pipx install bandit
pip install ruff

# Run everything
./run_checks.sh
```

This runs:
1. Test harness (`test_exports.sh`)
2. Python linting (`lint_python.sh`) - if ruff installed
3. Bandit security scan (`run_bandit.sh`) - if bandit installed
4. ShellCheck linting (`run_shellcheck.sh`) - if shellcheck installed

All optional tools are skipped automatically if not installed.

## Security Scan Results

### Current Status

- **Bandit:** ✓ 0 issues found (174 lines scanned)
- **ShellCheck:** ✓ 0 critical issues (style recommendations only)
- **Security fuzzing:** ✓ 0 vulnerabilities (18/18 attacks blocked)
- **Test harness:** ✓ All tests passing

### What Each Tool Catches

**Bandit catches:**
- Hardcoded passwords/secrets
- SQL injection risks
- Shell injection vulnerabilities
- Insecure cryptographic functions
- Unsafe deserialization
- Assert statements in production code

**ShellCheck catches:**
- Unquoted variables causing word splitting
- Command injection vulnerabilities
- TOCTOU race conditions
- Incorrect conditionals
- Quoting and escaping issues
- Best practice violations

**Security fuzzing tests catch:**
- Command injection attacks
- Path traversal attempts
- Input length attacks
- Special character handling issues

## Troubleshooting

### Bandit "No issues identified"

This is good! It means no security issues were found.

### ShellCheck "style" warnings

Style warnings (SC2250, SC2292) are recommendations, not security issues. They suggest:
- Using `${var}` instead of `$var`
- Using `[[ ]]` instead of `[ ]` for tests
- Declaring variables separately from assignment

These are optional improvements and don't affect security.

### Snyk "SNYK_TOKEN not set"

The Snyk scan will be skipped if `SNYK_TOKEN` is not configured. This is optional - see "Setup for GitHub Actions" above.

### GitHub Actions failing

1. Check the Actions tab for error details
2. Verify all secrets are set correctly
3. Ensure workflow file syntax is valid
4. Check tool installation in workflow

## Security Best Practices

1. **Run checks before commit:**
   ```bash
   ./run_checks.sh
   ```

2. **Review security scan results:**
   - Don't ignore Bandit warnings
   - Fix ShellCheck errors (not just warnings)
   - Address security fuzzing test failures immediately

3. **Keep dependencies updated:**
   - Monitor Snyk results
   - Update Python packages regularly
   - Check for security advisories

4. **Test with real data:**
   - Run exports on actual clusters
   - Validate anonymization works correctly
   - Check file permissions on sensitive files

---

**Last updated:** 2026-02-12
