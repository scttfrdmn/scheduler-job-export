# Claude Code Instructions

This file contains instructions for AI assistants (like Claude) working on this project.

## Project Overview

This project provides scripts for exporting job history and cluster configuration from HPC schedulers (SLURM, PBS, LSF, UGE, HTCondor). It emphasizes security, data validation, and anonymization.

## Project Management

**⚠️ IMPORTANT: We use GitHub Issues for task tracking, NOT markdown TODO files.**

### GitHub-Based Workflow

- **Issues**: Track all tasks, bugs, and enhancements in GitHub Issues
- **Labels**: Use proper labels (type, priority, component, scheduler)
- **Milestones**: Link issues to appropriate milestones (v1.0, v1.1, v1.2, Future)
- **Project Board**: https://github.com/users/scttfrdmn/projects/24

### Commands

```bash
# View all issues
gh issue list

# View issues by priority
gh issue list --label "priority: high"

# View issues by milestone
gh issue list --milestone "v1.0 - Production Ready"

# Create new issue
gh issue create --title "..." --body "..." --label "type: bug" --label "priority: high"

# View project board
gh project view 24 --owner scttfrdmn
```

### DO NOT
- ❌ Create TODO.md or TASKS.md files
- ❌ Add TODO comments in code without creating GitHub issues
- ❌ Track tasks in documentation files
- ❌ Use TaskCreate/TaskUpdate tools (use GitHub Issues instead)

### DO
- ✅ Create GitHub issues for all work items
- ✅ Reference issues in commits: `Fix #123: description`
- ✅ Link issues in PRs: `Closes #123`
- ✅ Update issue status with labels (`status: in progress`, etc.)
- ✅ Add proper labels (type, priority, component)

## Architecture

### File Organization

```
.
├── export_*.sh              # Scheduler-specific export scripts
├── anonymize_cluster_data.sh # Data anonymization
├── security_logging.sh      # Security audit logging
├── validation.sh            # Input validation library
├── test_exports.sh          # Test harness
├── security_tests.sh        # Security fuzzing tests
├── run_checks.sh            # Run all quality checks
├── run_bandit.sh            # Python security scanner
├── run_shellcheck.sh        # Bash security linter
├── .github/workflows/       # CI/CD workflows
└── docs/                    # Documentation
```

### Key Components

1. **Export Scripts** (`export_*.sh`)
   - Scheduler-specific data extraction
   - Input validation via `validation.sh`
   - Security logging via `security_logging.sh`
   - Output: CSV files with job data

2. **Anonymization** (`anonymize_cluster_data.sh`)
   - Cryptographic hashing (SHA256)
   - Consistent mapping (same input → same output)
   - Preserves patterns for analysis

3. **Security** (`security_logging.sh`, `validation.sh`)
   - Input validation (command injection, path traversal)
   - Security audit logging
   - File permission enforcement (600)
   - SHA256 checksum generation

4. **Testing** (`test_exports.sh`, `security_tests.sh`)
   - 9 core tests (Python, Bash, syntax, anonymization, permissions)
   - 18 security fuzzing tests (injection attacks)
   - All must pass before deployment

## Security Standards

**Security Grade: A** (independently verified)

### Security Requirements

- ✅ All input MUST be validated via `validation.sh`
- ✅ All security events MUST be logged via `security_logging.sh`
- ✅ Sensitive files MUST have 600 permissions
- ✅ NO command injection vulnerabilities
- ✅ NO path traversal vulnerabilities
- ✅ Security tests MUST pass (18/18)

### Security Scanning

Automated scans run on every commit:
- **Bandit**: Python security scanner
- **ShellCheck**: Bash security linter
- **Snyk**: Dependency vulnerability scanner
- **Security fuzzing**: Injection attack tests

All scans must pass. See `.github/workflows/security.yml`.

### Adding New Code

When adding new code:

1. **Input validation**: Use `validation.sh` functions
   ```bash
   source validation.sh
   validate_date_format "$date"
   validate_file_path "$file"
   ```

2. **Security logging**: Log security events
   ```bash
   source security_logging.sh
   log_export_start "$scheduler" "$@"
   log_export_complete "$scheduler" "$records" "$output"
   ```

3. **Error handling**: Sanitize errors in non-VERBOSE mode
   ```bash
   if [ -z "${VERBOSE:-}" ]; then
       echo "ERROR: Operation failed" >&2
   else
       echo "ERROR: Detailed error: $error_detail" >&2
   fi
   ```

4. **File permissions**: Set secure permissions
   ```bash
   chmod 600 "$sensitive_file"
   ```

## Testing Standards

### Required Tests

All changes must pass:
- ✅ `./test_exports.sh` - 9 core tests
- ✅ `./security_tests.sh` - 18 security tests
- ✅ `./lint_python.sh` - Python linting (if ruff installed)
- ✅ `./run_bandit.sh` - Python security scan (if bandit installed)
- ✅ `./run_shellcheck.sh` - Bash linting (if shellcheck installed)

Run all checks:
```bash
./run_checks.sh
```

### CI/CD

GitHub Actions runs on every push:
- Security scanning (Bandit, ShellCheck, Snyk)
- Security fuzzing tests
- Test harness
- Python linting

See `.github/workflows/security.yml`.

## Code Style

### Bash

- Use `set -euo pipefail` at script start
- Source libraries: `source validation.sh`, `source security_logging.sh`
- Validate all input before use
- Log security events
- Use `${var}` not `$var` (SC2250 - recommended, not required)
- Use `[[ ]]` not `[ ]` (SC2292 - recommended, not required)
- Add descriptive comments for complex logic
- Keep functions focused and small

### Python

- Embedded in bash heredocs: `python3 - <<'PYTHON_EOF'`
- Follow PEP 8 (enforced by ruff)
- Use standard library only (no external dependencies)
- Handle errors gracefully
- Validate input data

### Commit Messages

Follow conventional commits:
```
type(scope): description

- type: feat, fix, docs, test, refactor, security
- scope: component name (export, anonymization, validation, ci)
- description: imperative mood ("add" not "added")
```

Reference issues:
```
fix(validation): prevent path traversal in file validation

- Add absolute path check
- Add parent directory validation
- Fixes #123
```

## Documentation

### Required Documentation

When adding features:
- ✅ Update README.md with usage examples
- ✅ Update TESTING.md if adding tests
- ✅ Update SECURITY.md if security-related
- ✅ Add comments in code for complex logic
- ✅ Create GitHub issue for tracking

### Documentation Files

- **README.md**: User-facing documentation, getting started
- **TESTING.md**: Testing guide, test infrastructure
- **SECURITY.md**: Security policy, vulnerability reporting
- **SECURITY_SETUP.md**: Security tool setup and configuration
- **PROJECT_MANAGEMENT.md**: GitHub workflow, labels, milestones
- **CLAUDE.md**: This file - AI assistant instructions

## Common Tasks

### Adding a New Scheduler

1. Create GitHub issue: `gh issue create --title "Add support for <scheduler>"`
2. Create export script: `export_<scheduler>_comprehensive.sh`
3. Add input validation
4. Add security logging
5. Add to README.md Quick Start
6. Add tests
7. Commit: `feat(export): add <scheduler> support (closes #<issue>)`

### Fixing a Security Issue

1. Create GitHub issue with `type: security` label (or use GitHub Security Advisory for vulnerabilities)
2. Write failing security test in `security_tests.sh`
3. Fix the vulnerability
4. Verify test passes
5. Run all security scans
6. Commit: `security(component): fix <issue> (fixes #<issue>)`
7. Update SECURITY.md

### Adding New Tests

1. Create GitHub issue with `type: testing` label
2. Add test to `test_exports.sh` or `security_tests.sh`
3. Document test in TESTING.md
4. Commit: `test: add <test description> (closes #<issue>)`

### Refactoring

1. Create GitHub issue with `type: refactor` label
2. Ensure all tests pass before refactoring
3. Make changes
4. Ensure all tests still pass
5. Run security scans
6. Commit: `refactor(component): <description> (closes #<issue>)`

## Release Process

### Version Numbering

Semantic versioning: `MAJOR.MINOR.PATCH`
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Tagging a Release

1. Ensure all tests pass
2. Update version references
3. Create annotated tag:
   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0: Production ready"
   git push origin v1.0.0
   ```
4. Create GitHub release with changelog
5. Close milestone

### Release Checklist

- [ ] All milestone issues completed
- [ ] All tests passing (CI/CD green)
- [ ] All security scans passing
- [ ] Documentation updated
- [ ] CHANGELOG updated (if exists)
- [ ] Version number updated in relevant files

## Getting Help

- **Issues**: https://github.com/scttfrdmn/scheduler-job-export/issues
- **Security**: See SECURITY.md for vulnerability reporting
- **Testing**: See TESTING.md for test documentation
- **Project Management**: See PROJECT_MANAGEMENT.md for GitHub workflow

## AI Assistant Best Practices

1. **Check GitHub Issues First**: Before suggesting new work, check existing issues
2. **Create Issues for Work**: Always create GitHub issues for new tasks
3. **Reference Issues**: Include issue numbers in commits and PRs
4. **Run Tests**: Always run `./run_checks.sh` before committing
5. **Security First**: Never compromise security for convenience
6. **Document Changes**: Update relevant documentation
7. **Follow Standards**: Adhere to security and testing standards
8. **Use Labels**: Properly label all GitHub issues
9. **Link to Milestones**: Associate issues with appropriate milestones
10. **No TODO Files**: Use GitHub Issues, not markdown files

---

**Last updated:** 2026-02-12
