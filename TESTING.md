# Testing and Linting

This repository includes test and linting infrastructure to ensure code quality.

## Quick Start

Run all checks at once:

```bash
./run_checks.sh
```

This runs both tests and linting (if available).

## Running Tests

Test harness validates:
- Python availability and version
- Bash version compatibility
- Script executability
- Python syntax in embedded code
- Standard library imports
- Anonymization functionality
- Documentation completeness
- Shell script quality (if shellcheck available)

```bash
./test_exports.sh
```

**Expected output:**
```
================================================================
TEST SUMMARY
================================================================

Tests passed: 7
Tests failed: 0

✓ ALL TESTS PASSED
```

## Running Python Linting

Lint all embedded Python code:

```bash
./lint_python.sh
```

This script:
1. Extracts Python code from bash heredocs
2. Runs `ruff` linter on extracted code
3. Reports any style or quality issues

**Prerequisites:**
```bash
# Install ruff (fast Python linter)
pip install ruff
# or
pipx install ruff
```

**Configuration:** See `pyproject.toml` for ruff settings.

## Security Scanning

### Bandit (Python Security Scanner)

Bandit performs static analysis of Python code to find common security issues.

```bash
./run_bandit.sh
```

**Prerequisites:**
```bash
# Install bandit
pip install bandit
# or
pipx install bandit
```

**What it checks:**
- SQL injection vulnerabilities
- Shell injection risks
- Hardcoded passwords/secrets
- Unsafe YAML loading
- Assert usage in production
- Insecure cryptographic functions
- Subprocess security issues

**Configuration:** See `.bandit` for excluded tests and severity thresholds.

### ShellCheck (Bash Security Linter)

ShellCheck analyzes bash scripts for security issues and best practices.

```bash
./run_shellcheck.sh
```

**Prerequisites:**
```bash
# macOS
brew install shellcheck

# Ubuntu/Debian
apt-get install shellcheck
```

**What it checks:**
- Command injection vulnerabilities
- Unquoted variables that could cause issues
- Missing error handling
- Race conditions (TOCTOU)
- Incorrect conditionals
- Quoting and escaping issues
- Best practice violations

**Configuration:** See `.shellcheckrc` for disabled checks and shell dialect.

### Security Fuzzing Tests

Comprehensive tests for input validation and injection protection:

```bash
./security_tests.sh
```

Tests protection against:
- Command injection (7 attack patterns)
- Path traversal (3 attack patterns)
- Input length attacks (2 patterns)
- Special characters (5 patterns)

All tests must pass (0 vulnerabilities) before deployment.

## What Gets Tested

### Test Coverage

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| Python availability | Check Python 3.6+ installed | `python3 --version` succeeds |
| Bash version | Check Bash 3.2+ available | Bash major version >= 3 |
| Script executability | All export scripts have +x | All `.sh` files executable |
| Python syntax | Embedded Python code is valid | All heredocs compile without errors |
| Standard library | Required modules available | csv, sys, datetime, re, os, etc. |
| Anonymization | Test with sample data | Output creates proper anonymized CSV |
| Documentation | README has key sections | Quick Start, Requirements, etc. present |
| Shell quality | Shellcheck validation | No major shellcheck warnings (optional) |

### Python Code Linting

The linter checks:
- **Code style:** PEP 8 compliance
- **Import order:** Proper import organization (isort)
- **Common bugs:** Flake8-bugbear patterns
- **Comprehensions:** Unnecessary list/dict comprehensions
- **Naming:** PEP 8 naming conventions
- **Modern Python:** Upgrade suggestions for Python 3.6+

**Linter rules:**
- ✓ pycodestyle (E, W)
- ✓ pyflakes (F)
- ✓ isort (I)
- ✓ pep8-naming (N)
- ✓ pyupgrade (UP)
- ✓ flake8-bugbear (B)
- ✓ flake8-comprehensions (C4)

## Continuous Integration

This repository includes automated security checks via GitHub Actions.

### Security Workflow

See `.github/workflows/security.yml` for the complete CI/CD configuration.

**Runs on:**
- Every push to `main`
- Every pull request to `main`

**Security checks performed:**
1. **Bandit:** Python security scanning
2. **ShellCheck:** Bash security linting
3. **Ruff:** Python code quality
4. **Security fuzzing:** Injection attack tests
5. **Test harness:** Full test suite
6. **Snyk:** Dependency vulnerability scanning (main branch only)

**Viewing results:**
- GitHub Actions tab shows all workflow runs
- Failed checks block pull request merging
- Security issues are reported in workflow logs

### Custom CI Pipeline

Add to your own CI pipeline:

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install ruff bandit
          sudo apt-get install shellcheck
      - name: Run tests
        run: ./test_exports.sh
      - name: Run security checks
        run: |
          ./run_bandit.sh
          ./run_shellcheck.sh
          ./security_tests.sh
      - name: Run linter
        run: ./lint_python.sh
```

## Pre-commit Hooks

Run checks before committing:

```bash
# Add to .git/hooks/pre-commit
#!/bin/bash
./run_checks.sh
```

Or use the `pre-commit` framework:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: test-exports
        name: Test Export Scripts
        entry: ./test_exports.sh
        language: system
        pass_filenames: false
      - id: lint-python
        name: Lint Python Code
        entry: ./lint_python.sh
        language: system
        pass_filenames: false
```

## Manual Testing

Test individual scripts with sample data:

### Test Anonymization

```bash
# Create sample data
cat > test_input.csv << 'EOF'
user,group,account,job_id,nodelist,cpus
alice,research,proj_a,12345,node001,16
bob,physics,proj_b,12346,node002,32
EOF

# Test anonymization
./anonymize_cluster_data.sh \
  test_input.csv \
  test_output.csv \
  test_mapping.txt

# Verify output
cat test_output.csv
# Should show: user_0001, user_0002, node_0001, etc.
```

### Test Export Scripts

Since export scripts require actual scheduler data, manual testing requires:

1. **Access to scheduler:** Commands like `sacct`, `bhist`, `qacct`, etc.
2. **Historical data:** Accounting logs with job history
3. **Proper permissions:** May need admin/sudo access

**Example manual test (SLURM):**

```bash
# Test SLURM export with recent jobs
./export_with_users.sh $(date -d '7 days ago' '+%Y-%m-%d') $(date '+%Y-%m-%d')

# Verify output
head -10 slurm_jobs_with_users_*.csv
wc -l slurm_jobs_with_users_*.csv
```

## Troubleshooting

### "ruff: command not found"

Install ruff:
```bash
pip install ruff
# or
pipx install ruff
```

Or skip linting (tests will still run):
```bash
./test_exports.sh  # Tests only, no linting
```

### "shellcheck: command not found"

Shellcheck is optional. Install with:
```bash
# macOS
brew install shellcheck

# Ubuntu/Debian
apt-get install shellcheck

# Or skip this test
```

### Python syntax errors in tests

If tests report syntax errors:

1. **Check Python version:** Requires Python 3.6+
2. **Validate heredocs:** Ensure `PYTHON_EOF` markers are correct
3. **Run directly:** Extract and test problematic code manually

### Test failures after modifications

After editing scripts:

1. **Run tests:** `./test_exports.sh`
2. **Fix syntax:** Address any Python syntax errors
3. **Run linting:** `./lint_python.sh` (if available)
4. **Fix style:** Address linting warnings
5. **Manual test:** Test with real scheduler data if possible

## Adding New Tests

To add tests to `test_exports.sh`:

```bash
# Add new test function
echo "Test N: Your test description"
if [[ your_test_condition ]]; then
    pass_test "Test passed successfully"
else
    fail_test "Test failed because..."
fi
echo ""
```

## File Structure

```
.
├── pyproject.toml                    # Ruff configuration
├── .bandit                           # Bandit configuration
├── .shellcheckrc                     # ShellCheck configuration
├── run_checks.sh                     # Run all checks
├── test_exports.sh                   # Test harness
├── lint_python.sh                    # Python linting
├── run_bandit.sh                     # Bandit security scanner
├── run_shellcheck.sh                 # ShellCheck linter
├── security_tests.sh                 # Security fuzzing tests
├── .github/workflows/security.yml    # CI/CD security workflow
├── TESTING.md                        # This file
└── export_*.sh                       # Scripts being tested
```

## Best Practices

1. **Run before commit:** Always run `./run_checks.sh` before committing
2. **Fix warnings:** Address linting warnings, not just errors
3. **Test with real data:** Manually test exports on actual clusters when possible
4. **Keep tests fast:** Tests should complete in < 30 seconds
5. **Document changes:** Update TESTING.md if adding new test types

## Future Enhancements

Potential improvements:

- [ ] Unit tests for Python functions
- [ ] Integration tests with mock scheduler data
- [ ] Performance benchmarks
- [ ] Code coverage reporting
- [x] Automated security scanning (✓ Completed: Bandit, ShellCheck, Snyk)
- [ ] Docker-based testing environment
- [ ] Multi-scheduler CI testing

---

**Last updated:** 2026-02-12
