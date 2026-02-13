# Scheduler Data Export

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.6+-green.svg)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/Bash-3.2+-orange.svg)](https://www.gnu.org/software/bash/)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)](#testing-and-quality-assurance)
[![Code Style](https://img.shields.io/badge/Code%20Style-Ruff-black.svg)](https://github.com/astral-sh/ruff)

[![Security Checks](https://github.com/scttfrdmn/scheduler-job-export/actions/workflows/security.yml/badge.svg)](https://github.com/scttfrdmn/scheduler-job-export/actions/workflows/security.yml)
[![Known Vulnerabilities](https://snyk.io/test/github/scttfrdmn/scheduler-job-export/badge.svg)](https://snyk.io/test/github/scttfrdmn/scheduler-job-export)

Scripts for collecting **job history** and **cluster configuration** from HPC schedulers.

**Supported Schedulers:** SLURM, IBM Spectrum LSF, PBS/Torque, UGE/SGE, HTCondor

---

## Quick Start

### 1. Export Job Data

```bash
# SLURM
./export_with_users.sh 2024-01-01 2024-12-31

# LSF
./export_lsf_comprehensive.sh 2024/01/01 2024/12/31

# PBS/Torque (often needs sudo)
sudo ./export_pbs_comprehensive.sh 20240101 20241231

# UGE/SGE
./export_uge_comprehensive.sh 01/01/2024 12/31/2024

# HTCondor
./export_htcondor_data.sh
```

**Omit dates to export last year by default.** Each scheduler uses its native date format.

### 2. Export Cluster Configuration

This is a **separate required step** - cluster config is not included in job data export.

```bash
# Run the config export for your scheduler
./export_slurm_cluster_config.sh
./export_lsf_cluster_config.sh
./export_pbs_cluster_config.sh
./export_uge_cluster_config.sh
```

### 3. Anonymize for Sharing (Optional)

```bash
./anonymize_cluster_data.sh input.csv output.csv mapping.txt
chmod 600 mapping.txt  # Secure the mapping file
```

> **Security Note:** Scripts include input validation, injection protection, audit logging, and secure file permissions. See [SECURITY.md](SECURITY.md) for details.

---

## What Gets Exported

### Job Data Format

All scripts produce standardized CSV with these columns:

| Column | Description |
|--------|-------------|
| `user` | Username |
| `group` | User's group |
| `account` | Project/accounting identifier |
| `job_id` | Unique job identifier |
| `job_name` | Job name (if available) |
| `cpus_req` | CPUs requested |
| `mem_req` | Memory requested (MB) |
| `mem_used` | Peak memory used (MB) |
| `cpu_time_used` | CPU time consumed (seconds) |
| `walltime_used` | Wall clock time (seconds) |
| `nodes` | Number of nodes |
| `nodelist` | Nodes where job ran |
| `submit_time` | Submission timestamp |
| `start_time` | Start timestamp |
| `end_time` | Completion timestamp |
| `exit_status` | Exit code (0=success) |
| `cpus_alloc` | CPUs actually allocated |
| `partition` | SLURM partition/queue name |
| `qos` | Quality of Service policy |
| `priority` | Job priority value |
| `reservation` | Reservation name (if used) |
| `gpu_count` | Total GPUs allocated |
| `gpu_types` | GPU models with counts (e.g., "v100:2,a100:1") |
| `node_type` | Node category (gpu/highmem/largemem/compute) |

**Key Features:**
- **All outcomes captured:** Success, failure, timeout, cancellation, OOM
- **Resource efficiency:** Compare requested vs. used resources
- **GPU tracking:** Automatic detection of GPU count and types (SLURM)
- **Node classification:** Hardware-based detection of node types (SLURM)
- **Scheduler-specific:** Some include `queue`, `status`, `pe_name` columns

### Cluster Configuration Format

| Column | Description |
|--------|-------------|
| `hostname` | Node hostname |
| `cpus` | CPUs per node |
| `memory_mb` | Memory per node (MB) |
| `node_type` | compute, gpu, highmem, etc. |
| `state` | idle, allocated, down, etc. |
| `partition` | Queue/partition name |

---

## Requirements

**No installation needed** - uses standard Unix tools:

- **Bash** 3.2+
- **Python** 3.6+ (standard library only, no pip packages)
- **Scheduler commands:** `sacct`, `bhist`, `qacct`, etc.
- **Permissions:** Read access to scheduler accounting data (may need sudo for PBS)

See [detailed requirements](#detailed-requirements) for scheduler-specific needs.

---

## Usage Guide

### Date Format Quick Reference

| Scheduler | Format | Example |
|-----------|--------|---------|
| SLURM | `YYYY-MM-DD` | `2024-01-31` |
| LSF | `YYYY/MM/DD` | `2024/01/31` |
| PBS/Torque | `YYYYMMDD` | `20240131` |
| UGE/SGE | `MM/DD/YYYY` | `01/31/2024` |
| HTCondor | N/A | Uses all history |

All scripts: `./export_script [START_DATE] [END_DATE]`

### SLURM

```bash
# Basic export
./export_with_users.sh                        # Last year
./export_with_users.sh 2024-01-01 2024-12-31 # Specific range

# Cluster config
./export_slurm_cluster_config.sh

# Dynamic date ranges
./export_with_users.sh $(date -d '90 days ago' '+%Y-%m-%d') $(date '+%Y-%m-%d')
```

**Output:** `slurm_jobs_with_users_YYYYMMDD.csv` (25 columns), `slurm_cluster_config.csv`

**GPU and Advanced Resource Tracking:**

SLURM exports include enhanced resource tracking for modern HPC environments:

- **GPU Detection:** Automatically extracts GPU count and types from TRES allocation
  - Example: `gpu_count=4`, `gpu_types="v100:2,a100:2"`
  - Supports heterogeneous GPU jobs (multiple GPU types)
  - Empty for non-GPU jobs (not "0" or "none")

- **Node Type Classification:** Multi-tier detection based on:
  1. Hardware presence (GPU count > 0 → "gpu")
  2. Partition name patterns (highmem, largemem, gpu)
  3. QoS policy hints (gpu-qos, highmem-qos)
  4. Default fallback ("compute")

- **Scheduling Information:** Partition, QoS, priority, and reservation data for advanced analysis

**Example Output for GPU Job:**
```csv
user,group,account,job_id,...,gpu_count,gpu_types,node_type
alice,research,proj123,12345,...,4,"v100:4",gpu
bob,physics,proj456,12346,...,2,"a100:2",gpu
charlie,chem,proj789,12347,...,"","",compute
```

This enables accurate Service Unit (SU) calculations where GPUs represent 50%+ of resource value.

### LSF

```bash
# Basic export
./export_lsf_comprehensive.sh                 # Last year
./export_lsf_comprehensive.sh 2024/01/01 2024/12/31

# Cluster config
./export_lsf_cluster_config.sh

# Background execution for large exports
nohup ./export_lsf_comprehensive.sh 2024/01/01 2024/12/31 &
```

**Output:** `lsf_jobs_comprehensive_YYYYMMDD.csv` (20 columns), `lsf_cluster_config.csv`

**Scheduling and Priority Tracking:**
- Now includes `qos` (Quality of Service from Project Name or Service Class)
- Now includes `priority` (job priority value)
- Priority-based accounting for fair share analysis
- QoS-specific weight factors for SU calculations

### PBS/Torque

```bash
# Basic export (usually needs sudo)
sudo ./export_pbs_comprehensive.sh            # Last year
sudo ./export_pbs_comprehensive.sh 20240101 20241231

# Cluster config
./export_pbs_cluster_config.sh

# Verbose mode for debugging
VERBOSE=1 sudo ./export_pbs_comprehensive.sh 20240101 20241231
```

**Output:** `pbs_jobs_with_users_YYYYMMDD.csv` (18 columns), `pbs_cluster_config.csv`

**Enhanced Resource Tracking:**
- Now includes `mem_used`, `cpu_time_used`, `walltime_used`, `cpus_alloc`
- Compare requested vs. actual resource usage
- Accurate Service Unit calculations based on actual consumption

### UGE/SGE

```bash
# Basic export
./export_uge_comprehensive.sh                 # Last year
./export_uge_comprehensive.sh 01/01/2024 12/31/2024

# Cluster config
./export_uge_cluster_config.sh

# Check available date range
qacct -b 01/01/2020 -e 01/02/2020
```

**Output:** `uge_jobs_with_users_YYYYMMDD.csv`, `uge_cluster_config.csv`

**Note:** UGE captures parallel environment (PE) jobs with `pe_name` and `slots` columns.

### HTCondor

```bash
# Export all available history
./export_htcondor_data.sh

# Or specify days back
./export_htcondor_data.sh 365  # Last 365 days
```

**Output:** `htcondor_jobs_with_users_YYYYMMDD.csv`

### Auto-Detection

Don't know your scheduler?

```bash
./export_cluster_configs_all.sh
```

Automatically detects your scheduler and runs the appropriate export.

---

## Anonymization

Replace usernames, groups, and hostnames with anonymous IDs for secure sharing.

### Usage

```bash
./anonymize_cluster_data.sh input.csv output.csv mapping.txt
chmod 600 mapping.txt  # Secure the mapping file
```

### Example

**Before:**
```csv
user,group,nodelist,cpus
alice,research,node-gpu-01.hpc.edu,16
bob,physics,compute-a001.org,32
```

**After:**
```csv
user,group,nodelist,cpus
user_0001,group_A,node_0001,16
user_0002,group_B,node_0002,32
```

### Features

- **Deterministic:** Same user → same ID across files
- **Three-way:** Users, groups, and hostnames
- **Secure:** Original identities not recoverable without mapping file
- **Preserves structure:** Behavioral patterns remain valid

**⚠️ Keep `mapping.txt` private!** Without it, anonymization is permanent.

### Complete Workflow

```bash
# 1. Export data
./export_with_users.sh 2024-01-01 2024-12-31
./export_slurm_cluster_config.sh

# 2. Anonymize both files
./anonymize_cluster_data.sh slurm_jobs_with_users_20260212.csv jobs_anon.csv mapping.txt
./anonymize_cluster_data.sh slurm_cluster_config.csv config_anon.csv mapping.txt

# 3. Share anonymized files (NOT the mapping!)
scp jobs_anon.csv config_anon.csv remote:~/data/

# 4. Secure or encrypt the mapping
chmod 600 mapping.txt
gpg --encrypt --recipient you@example.com mapping.txt
```

---

## Testing and Quality Assurance

### Run All Checks

```bash
./run_checks.sh  # Runs tests + linting
```

### Test Harness

```bash
./test_exports.sh
```

Validates:
- Python/Bash version compatibility
- Script executability
- Python syntax in embedded code
- Anonymization functionality
- File permissions security
- Documentation completeness

### Security Fuzzing

```bash
./security_tests.sh
```

Tests protection against:
- Command injection (7 tests)
- Path traversal (3 tests)
- Input length attacks (2 tests)
- Special characters (5 tests)

### Python Linting

```bash
pip install ruff  # Optional but recommended
./lint_python.sh
```

### Security Scanning

**Bandit (Python Security Scanner):**
```bash
pip install bandit  # or: pipx install bandit
./run_bandit.sh
```

**ShellCheck (Bash Security Linter):**
```bash
# macOS
brew install shellcheck

# Ubuntu/Debian
apt-get install shellcheck

./run_shellcheck.sh
```

**Automated CI/CD:**
All security checks run automatically on every push and pull request via GitHub Actions. See `.github/workflows/security.yml`.

> **Note:** Snyk vulnerability scanning requires a `SNYK_TOKEN` secret. See [SECURITY_SETUP.md](SECURITY_SETUP.md) for setup instructions.

See [TESTING.md](TESTING.md) for complete testing documentation.

---

## Security

This project implements comprehensive security measures with automated scanning and validation.

### Security Features

**Input Validation:**
- Command injection protection (18 attack patterns tested)
- Path traversal prevention
- Input length validation
- Special character sanitization

**Automated Security Scanning:**
- **Bandit**: Python security scanner (AST-based static analysis)
- **ShellCheck**: Bash security linter (best practices and vulnerabilities)
- **Snyk**: Dependency vulnerability scanning
- **Security fuzzing**: 18 injection attack tests, all passing

**Data Protection:**
- Secure file permissions (600) on sensitive files
- SHA256 checksums for data integrity
- Anonymization with cryptographic mapping
- Security audit logging

### Security Status

All security checks run automatically on every commit via GitHub Actions:

[![Security Checks](https://github.com/scttfrdmn/scheduler-job-export/actions/workflows/security.yml/badge.svg)](https://github.com/scttfrdmn/scheduler-job-export/actions/workflows/security.yml)
[![Known Vulnerabilities](https://snyk.io/test/github/scttfrdmn/scheduler-job-export/badge.svg)](https://snyk.io/test/github/scttfrdmn/scheduler-job-export)

**Current Results:**
- ✅ Bandit: 0 security issues (174 lines scanned)
- ✅ ShellCheck: 0 critical errors
- ✅ Security fuzzing: 18/18 tests passing
- ✅ Input validation: All injection attempts blocked

### Security Documentation

- **[SECURITY.md](SECURITY.md)** - Security policy and vulnerability reporting
- **[SECURITY_SETUP.md](SECURITY_SETUP.md)** - Security tool setup and configuration
- **[TESTING.md](TESTING.md)** - Detailed testing documentation including security tests

### Reporting Security Issues

If you discover a security vulnerability, please follow our [security policy](SECURITY.md) for responsible disclosure.

---

## Troubleshooting

### Command Not Found

```bash
# SLURM
module load slurm
which sacct

# LSF
source /path/to/lsf/conf/profile.lsf

# UGE
source /path/to/sge/default/common/settings.sh
```

### Permission Denied

```bash
# PBS usually needs sudo
sudo ./export_pbs_comprehensive.sh 20240101 20241231

# LSF needs admin flag
bhist -a  # Requires admin privileges
```

### Export Too Slow

```bash
# Use shorter date ranges
./export_lsf_comprehensive.sh 2024/10/01 2024/10/31

# Or run in background
nohup ./export_lsf_comprehensive.sh 2024/01/01 2024/12/31 &
```

### Encoding Issues

```bash
export LC_ALL=en_US.UTF-8
./export_with_users.sh
```

### Verbose Debugging

```bash
# Enable verbose error messages
VERBOSE=1 ./export_pbs_comprehensive.sh 20240101 20241231
```

---

## Advanced Topics

### Scheduler-Specific Details

<details>
<summary><b>SLURM</b></summary>

**Advantages:**
- Fast exports with `sacct`
- Comprehensive data
- Usually no special permissions needed

**Limitations:**
- Limited retention period (often 30-90 days)
- May need slurmdbd for older data

**Tips:**
```bash
# Check retention period
sacct --starttime=2020-01-01 --endtime=2020-01-02 -X

# Export specific partition
sacct -r partition_name ...
```

</details>

<details>
<summary><b>LSF</b></summary>

**Advantages:**
- Rich history via `bhist`
- Good backwards compatibility

**Limitations:**
- Requires admin flag (`-a`) for all users
- Can be slow on large datasets

**Tips:**
```bash
# Test on small range first
bhist -a -l 2024/12/01 2024/12/01 | head

# Background for large exports
nohup ./export_lsf_comprehensive.sh 2024/01/01 2024/12/31 &
```

</details>

<details>
<summary><b>PBS/Torque</b></summary>

**Advantages:**
- Detailed accounting logs
- Long retention (often years)

**Limitations:**
- Usually requires sudo
- Log format varies by version

**Tips:**
```bash
# Check log location
ls -lh /var/spool/pbs/server_priv/accounting/

# Copy logs (one-time sudo)
sudo cp -r /var/spool/pbs/server_priv/accounting/ ~/pbs_logs/
```

</details>

<details>
<summary><b>UGE/SGE</b></summary>

**Advantages:**
- Structured `qacct` output
- Usually no special permissions
- Captures parallel environment (PE) jobs

**Limitations:**
- US date format (MM/DD/YYYY)
- May have data gaps
- Multi-node PE jobs show limited hostname info

**Parallel Environment Handling:**
- Queries PE configs via `qconf -sp`
- Calculates accurate node counts from allocation rules
- Captures PE name and slots in output

**Tips:**
```bash
# List parallel environments
qconf -spl

# View PE configuration
qconf -sp mpi

# Check available date range
qacct -b 01/01/2020 -e 01/02/2020
```

</details>

<details>
<summary><b>HTCondor</b></summary>

**Advantages:**
- Powerful query language
- Usually complete history

**Limitations:**
- Complex output format
- May need multiple queries

**Tips:**
```bash
# Check history size
condor_history -limit 10

# Time-based constraint
condor_history -constraint 'JobStartDate >= 1704067200'
```

</details>

### Expected File Sizes

| Jobs | CSV Size (uncompressed) |
|------|-------------------------|
| 10,000 | ~2 MB |
| 100,000 | ~20 MB |
| 1,000,000 | ~200 MB |
| 10,000,000 | ~2 GB |

**Tip:** Compress large files: `gzip jobs_export.csv` (typically 10-20% of original)

### Data Format Standardization

Normalize exports from multiple schedulers:

```bash
python3 standardize_cluster_config.py input_config.csv
# Output: input_config_standardized.csv
```

Converts all scheduler formats to common structure for cross-scheduler analysis.

---

## Reference

### Detailed Requirements

**All Schedulers:**
- Bash 3.2+ (tested on macOS, Linux, BSD)
- Python 3.6+ (standard library only: csv, sys, datetime, collections, re, os)
- Date command (GNU or BSD, auto-detected)
- Common Unix tools: wc, head, tail, grep, cut, sort, mktemp

**Scheduler-Specific:**
- **SLURM:** `sacct`, `sinfo`
- **LSF:** `bhist`, `bhosts` (may need `-a` for all users)
- **PBS/Torque:** `/var/spool/pbs/server_priv/accounting/`, `pbsnodes` (often needs sudo)
- **UGE/SGE:** `qacct`, `qhost`, `qconf`
- **HTCondor:** `condor_history`, `condor_status`

### Output File Locations

Scripts create timestamped files in current directory:

```
slurm_jobs_with_users_YYYYMMDD.csv       # SLURM job data
slurm_cluster_config.csv                 # SLURM cluster config
lsf_jobs_comprehensive_YYYYMMDD.csv      # LSF job data
lsf_cluster_config.csv                   # LSF cluster config
pbs_jobs_with_users_YYYYMMDD.csv         # PBS job data
pbs_cluster_config.csv                   # PBS cluster config
uge_jobs_with_users_YYYYMMDD.csv         # UGE job data
uge_cluster_config.csv                   # UGE cluster config
htcondor_jobs_with_users_YYYYMMDD.csv    # HTCondor job data
htcondor_cluster_config.csv              # HTCondor cluster config
```

### Security & Privacy Considerations

**Job data may contain:**
- Usernames and group memberships
- Job submission patterns
- Resource usage patterns

**Recommendations:**
1. Anonymize before sharing outside your organization
2. Encrypt during transfer (scp, sftp, encrypted email)
3. Secure storage with restricted access
4. Get institutional approval before collecting
5. Delete mapping files if not needed long-term

See [SECURITY.md](SECURITY.md) for comprehensive security documentation.

---

## Contributing

Contributions are welcome! See [open issues](https://github.com/scttfrdmn/scheduler-job-export/issues) for enhancement opportunities.

**Areas for enhancement:**
- Additional scheduler support
- Better error handling
- Performance optimizations
- Additional output formats (JSON, Parquet)

**Before contributing:**
1. Check [existing issues](https://github.com/scttfrdmn/scheduler-job-export/issues) or create a new one
2. Run `./run_checks.sh` to ensure tests pass
3. Test with real scheduler data when possible
4. Update documentation as needed
5. Reference issue numbers in commits: `Fix #123: description`

See [PROJECT_MANAGEMENT.md](PROJECT_MANAGEMENT.md) for workflow details, labels, and milestones.

---

## Support

**For issues or questions:**
1. Check the [troubleshooting section](#troubleshooting)
2. Review your scheduler's documentation
3. Test with a small date range first
4. Check file permissions and command availability

**What's NOT included:**
This is a data collection toolkit. It does NOT include:
- Analysis scripts
- Visualization tools
- Statistical analysis
- Machine learning models
- Cloud migration calculators

Export raw data, then analyze with your preferred tools (Python, R, Excel, etc.).

---

## License

Apache License 2.0 - See [LICENSE](LICENSE) file for details.

Copyright 2026 Scott Friedman

---

## Versioning

This project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) and maintains a changelog following [Keep a Changelog 1.0.0](https://keepachangelog.com/en/1.0.0/).

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality (backward compatible)
- **PATCH** version for bug fixes (backward compatible)

See [CHANGELOG.md](CHANGELOG.md) for detailed release notes and [Releases](https://github.com/scttfrdmn/scheduler-job-export/releases) for all versions.

**Current Version:** [v1.0.0](https://github.com/scttfrdmn/scheduler-job-export/releases/tag/v1.0.0)

---
