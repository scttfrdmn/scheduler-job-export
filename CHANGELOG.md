# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Unit tests for Python functions (#1)
- Integration tests with mock scheduler data (#2)
- Performance benchmarks and profiling (#3)
- Code coverage reporting (#4)
- Docker-based testing environment (#5)
- Multi-scheduler CI testing matrix (#6)
- Address ShellCheck style recommendations (#7)
- Refactor export scripts to reduce code duplication (#8)
- Configurable output formats (JSON, Parquet) (#9)
- Incremental exports with state tracking (#10)

## [1.0.0] - 2026-02-12

### Added
- **Scheduler Support**: Export job data from SLURM, IBM Spectrum LSF, PBS/Torque, UGE/SGE, and HTCondor
- **Job Data Export**: Comprehensive job history export with all scheduler-specific fields
- **Cluster Configuration Export**: Separate scripts for exporting cluster configuration
- **Data Anonymization**: Cryptographic anonymization with SHA256 hashing and consistent mapping
  - Anonymize usernames, groups, accounts, hostnames
  - Preserve data patterns for analysis
  - Bidirectional mapping files for reference
- **Input Validation**: Protection against command injection and path traversal attacks
  - Date format validation for all schedulers
  - File path validation with absolute path checks
  - Special character sanitization
- **Security Logging**: Comprehensive security audit logging
  - Export start/complete logging
  - Validation failure tracking
  - Permission issue logging
  - Security event recording
- **Security Features**:
  - SHA256 checksum generation and verification
  - Secure file permissions (600) on sensitive files
  - CSV column data validation
  - Array content validation before processing
  - Error message sanitization (VERBOSE mode)
- **Automated Security Scanning**:
  - Bandit Python security scanner
  - ShellCheck Bash security linter
  - Snyk dependency vulnerability scanner
  - 18 security fuzzing tests (command injection, path traversal, input length, special characters)
- **Testing Infrastructure**:
  - Test harness with 9 core tests
  - Security fuzzing test suite with 18 tests
  - Python linting with Ruff
  - Automated CI/CD with GitHub Actions
- **Documentation**:
  - Comprehensive README with Quick Start guide
  - TESTING.md with complete testing documentation
  - SECURITY.md with security policy and vulnerability reporting
  - SECURITY_SETUP.md with tool setup instructions
  - PROJECT_MANAGEMENT.md with GitHub workflow guide
  - CLAUDE.md with AI assistant instructions
- **Project Management**:
  - GitHub Issues with comprehensive label taxonomy (33 labels)
  - Milestones for release planning (v1.0, v1.1, v1.2, Future)
  - Project board for visual tracking
  - 10 enhancement issues for future development
- **Security Badges**: GitHub Actions and Snyk badges showing real-time security status

### Security
- **Security Grade A** (independently verified)
- Input validation blocks all 18 tested injection attack patterns
- Zero security issues found by Bandit (174 lines scanned)
- Zero critical errors found by ShellCheck
- Zero known vulnerabilities (Snyk)
- All security tests passing in CI/CD

### Infrastructure
- GitHub Actions workflow for automated security checks
- Pre-commit quality checks script (`run_checks.sh`)
- Configuration files: `.bandit`, `.shellcheckrc`, `pyproject.toml`
- Shell script quality validation
- Python syntax and import validation

## [0.1.0] - Initial Development

### Added
- Initial scheduler export scripts
- Basic anonymization functionality
- Core documentation

---

## Version History

- **[1.0.0]** - 2026-02-12 - Production ready release
- **[0.1.0]** - Initial development

## Links

- **Repository**: https://github.com/scttfrdmn/scheduler-job-export
- **Issues**: https://github.com/scttfrdmn/scheduler-job-export/issues
- **Releases**: https://github.com/scttfrdmn/scheduler-job-export/releases
- **Keep a Changelog**: https://keepachangelog.com/
- **Semantic Versioning**: https://semver.org/
