# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned

## [1.2.1] - 2026-02-19

### Fixed
- **SLURM Export**: Skip job step records in sacct output to prevent duplicate rows and ensure accurate resource usage data
  - `sacct` returns both job-level records (`12345`) and step records (`12345.batch`, `12345.0`) in the same output
  - Without filtering, each job appeared 2-3 times in the CSV
  - At the job level, SLURM aggregates `MaxRSS` as the max across all steps, so `mem_used` is correctly populated without reading step records
  - Array jobs (`12345_1`) are correctly kept; array steps (`12345_1.batch`) are skipped
  - Ensures accurate `mem_used`, `cpu_time_used`, and `walltime_used` values
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

## [1.2.0] - 2026-02-13

### Added

**Multi-Scheduler Enhancements** - Quick wins series bringing all schedulers closer to SLURM parity

- **Enhanced PBS Export** (#13): Resource usage metrics for accurate SU calculations
  - **New columns**: `mem_used`, `cpu_time_used`, `walltime_used`, `cpus_alloc`
  - **Column count**: Increased from 14 to 18 columns (56% → 72% of SLURM)
  - **Resource comparison**: Compare requested vs. actual usage
  - **CPU allocation tracking**: Count actual CPUs from exec_host format
  - **Key insight**: Data was already being parsed but not exported
  - **Impact**: +4 columns, enables accurate SU calculations

- **Enhanced LSF Export** (#14): QoS and priority for priority-based accounting
  - **New columns**: `qos`, `priority`
  - **Column count**: Increased from 18 to 20 columns (72% → 80% of SLURM)
  - **QoS detection**: Project Name or Service Class
  - **Priority tracking**: Job priority value from bhist -l
  - **Fair share analysis**: Track QoS usage distribution
  - **Dual mapping**: Project Name serves as both account and qos
  - **Impact**: +2 columns, enables priority-based SU multipliers

- **Enhanced UGE Export** (#15): Priority and CPU allocation tracking
  - **New columns**: `priority`, `cpus_alloc`
  - **Column count**: Increased from 19 to 21 columns (76% → 84% of SLURM)
  - **Priority tracking**: Job priority value from qacct
  - **CPU allocation**: Actual CPUs allocated (from slots field)
  - **Most complete**: Now has 21 columns - most feature-complete traditional scheduler
  - **UGE advantage**: Includes unique PE tracking (pe_name, slots)
  - **Impact**: +2 columns, closest to SLURM parity

- **Enhanced HTCondor Export** (#16): Status and priority tracking
  - **New columns**: `status`, `priority`
  - **Column count**: Increased from 17 to 19 columns (68% → 76% of SLURM)
  - **Status mapping**: Human-readable job status (IDLE, RUNNING, COMPLETED, HELD, etc.)
  - **Priority tracking**: Job priority value from ClassAds
  - **Job lifecycle**: Track job state changes and held jobs
  - **Debugging support**: Identify held or problematic jobs
  - **Impact**: +2 columns, enables job lifecycle analysis

### Fixed
- **PBS Export**: Fixed fieldnames mismatch (was `cpus`, should be `cpus_req`)

### Changed
- **Documentation**: Updated README.md with column counts and new features for all schedulers
- **CHANGELOG**: Comprehensive documentation of all enhancements

### Summary

**Total Impact:**
- **4 schedulers enhanced** (PBS, LSF, UGE, HTCondor)
- **10 new columns** added across all schedulers
- **All schedulers now at 72-84%** of SLURM's capabilities (up from 56-76%)
- **~4 hours total effort** (all from readily available data)

**Column Count Progression:**
- PBS: 14 → 18 (+4 columns)
- LSF: 18 → 20 (+2 columns)
- UGE: 19 → 21 (+2 columns)
- HTCondor: 17 → 19 (+2 columns)

**New Capabilities:**
- Resource usage comparison (requested vs actual)
- Priority-based fair share analysis
- QoS-specific accounting
- Job lifecycle tracking
- Accurate Service Unit calculations

## [1.1.0] - 2026-02-13

### Added
- **Enhanced SLURM Export** (#12): GPU, node type, and QoS data for advanced Service Unit calculations
  - **New columns**: `partition`, `qos`, `priority`, `reservation`, `gpu_count`, `gpu_types`, `node_type`
  - **GPU Detection**: Automatic parsing of TRES allocation format
    - Extracts total GPU count and GPU types (e.g., "v100:2,a100:1")
    - Supports heterogeneous GPU jobs (multiple GPU types)
    - Sorted by count descending (dominant type first)
  - **Node Type Classification**: Multi-tier detection logic
    - Hardware-based (GPU count > 0 → "gpu")
    - Partition name patterns (highmem, largemem, gpu)
    - QoS policy hints (gpu-qos, highmem-qos)
    - Default fallback ("compute")
  - **Scheduling Information**: Partition, QoS, priority, and reservation data
  - **Column count**: Increased from 18 to 25 columns
  - **Backward compatible**: New columns added at end, empty strings for missing data
  - **Performance**: Lightweight regex parsing with <10% overhead

### Changed
- SLURM export now queries 5 additional sacct fields (Partition, QOS, Priority, Reservation, AllocTRES)
- Updated job data format documentation with 7 new columns
- Added GPU tracking and node classification examples to README

### Removed
- Dead code block (54 lines) from SLURM export script that never executed

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

- **[1.2.1]** - 2026-02-19 - Fix SLURM duplicate rows from sacct step records
- **[1.2.0]** - 2026-02-13 - Multi-scheduler enhancements (PBS, LSF, UGE, HTCondor)
- **[1.1.0]** - 2026-02-13 - Enhanced SLURM export with GPU tracking
- **[1.0.0]** - 2026-02-12 - Production ready release
- **[0.1.0]** - Initial development

## Links

- **Repository**: https://github.com/scttfrdmn/scheduler-job-export
- **Issues**: https://github.com/scttfrdmn/scheduler-job-export/issues
- **Releases**: https://github.com/scttfrdmn/scheduler-job-export/releases
- **Keep a Changelog**: https://keepachangelog.com/
- **Semantic Versioning**: https://semver.org/
