# HPC Cluster Data Export Tools

Production-ready scripts for collecting **job history** and **cluster configuration** from HPC schedulers.

**Supported Schedulers:** SLURM, IBM Spectrum LSF, PBS/Torque, UGE/SGE, HTCondor

---

## Quick Start

**Complete data collection requires TWO exports:**
1. **Job data** (historical job submissions with dates)
2. **Cluster configuration** (current node/partition setup)

### 1. Export Job Data

All scripts accept optional date range arguments. If not provided, defaults to last 1 year.

```bash
# SLURM - Format: YYYY-MM-DD
./export_with_users.sh                        # Last year (default)
./export_with_users.sh 2024-01-01 2024-12-31 # Specific range

# LSF - Format: YYYY/MM/DD
./export_lsf_comprehensive.sh                 # Last year (default)
./export_lsf_comprehensive.sh 2024/01/01 2024/12/31

# PBS/Torque - Format: YYYYMMDD
sudo ./export_pbs_comprehensive.sh            # Last year (default)
sudo ./export_pbs_comprehensive.sh 20240101 20241231

# UGE/SGE - Format: MM/DD/YYYY
./export_uge_comprehensive.sh                 # Last year (default)
./export_uge_comprehensive.sh 01/01/2024 12/31/2024

# HTCondor
./export_htcondor_data.sh                     # All available history
```

**Note:** Each scheduler requires dates in its native format, but all work the same way:
```bash
./export_script [START_DATE] [END_DATE]
```

### 2. Export Cluster Configuration (Required)

**This is a separate required step** - cluster config is not included in job data export.

```bash
# SLURM
./export_slurm_cluster_config.sh

# LSF
./export_lsf_cluster_config.sh

# PBS
./export_pbs_cluster_config.sh

# UGE
./export_uge_cluster_config.sh
```

**Output:** CSV with node hostnames, CPU counts, memory, partitions, and current state.

### 3. Anonymize (Optional)

```bash
./anonymize_cluster_data.sh input.csv output.csv mapping.txt
```

---

## What Gets Exported

All scripts produce standardized CSV format with these core columns:

| Column | Description |
|--------|-------------|
| `user` | Username (lowercase, ready for anonymization) |
| `group` | User's group |
| `account` | Accounting/project identifier |
| `job_id` | Unique job identifier |
| `job_name` | Job name (if available) |
| `cpus` | Number of CPUs requested |
| `mem_req` | Memory requested (MB) |
| `nodes` | Number of nodes allocated |
| `nodelist` | List of nodes where job ran |
| `submit_time` | When job was submitted |
| `start_time` | When job started running |
| `end_time` | When job completed |
| `exit_status` | Job exit code |

**Scheduler-specific columns:**
- **LSF/PBS/UGE:** Include `queue` column
- **LSF/SLURM:** Include `status` column (job state)

**Cluster Config CSV:**

| Column | Description |
|--------|-------------|
| `hostname` | Node hostname |
| `cpus` | CPUs available on node |
| `memory_mb` | Memory available (MB) |
| `node_type` | Type of node |
| `state` | Current state |
| `partition` | Partition/queue name |

---

## Requirements

### All Schedulers

**No installation required** - these come with most Linux/Unix systems:
- **Bash:** 3.2+ (tested on macOS, Linux, BSD)
- **Python:** 3.6+ with standard library only
  - Uses: csv, sys, datetime, collections, re, os
  - No pip packages required
  - No virtual environment needed
- **Date command:** GNU date or BSD date (auto-detects and uses correct syntax)
- **Common Unix tools:** wc, head, tail, grep, cut, sort, mktemp (standard everywhere)

**Permissions:**
- Read access to scheduler accounting data (may require admin/sudo for some schedulers)

### SLURM
- `sacct` command available
- `sinfo` for cluster config

### LSF
- `bhist` command available
- `bhosts` for cluster config
- May require `-a` flag for all jobs

### PBS/Torque
- Access to accounting logs (usually `/var/spool/pbs/server_priv/accounting/`)
- `pbsnodes` command
- Often requires sudo

### UGE/SGE
- `qacct` command available
- `qhost` for cluster config

### HTCondor
- `condor_history` command available
- `condor_status` for cluster config

---

## Usage Examples

### SLURM Examples

```bash
# Export job data (last year by default)
./export_with_users.sh
# Output: slurm_jobs_with_users_YYYYMMDD.csv

# Export cluster configuration (REQUIRED)
./export_slurm_cluster_config.sh
# Output: slurm_cluster_config.csv

# Full year 2024
./export_with_users.sh 2024-01-01 2024-12-31

# Just one month (October)
./export_with_users.sh 2024-10-01 2024-10-31

# Last 90 days
./export_with_users.sh $(date -d '90 days ago' '+%Y-%m-%d') $(date '+%Y-%m-%d')
```

### LSF Examples

```bash
# Export job data (last year by default)
./export_lsf_comprehensive.sh
# Output: lsf_jobs_comprehensive_YYYYMMDD.csv

# Export cluster configuration (REQUIRED)
./export_lsf_cluster_config.sh
# Output: lsf_cluster_config.csv

# Full year 2024
./export_lsf_comprehensive.sh 2024/01/01 2024/12/31

# Just summer months
./export_lsf_comprehensive.sh 2024/06/01 2024/08/31
```

### PBS Examples

```bash
# Export job data (last year by default, usually needs sudo)
sudo ./export_pbs_comprehensive.sh
# Output: pbs_jobs_with_users_YYYYMMDD.csv

# Export cluster configuration (REQUIRED)
./export_pbs_cluster_config.sh
# Output: pbs_cluster_config.csv

# Full year 2024
sudo ./export_pbs_comprehensive.sh 20240101 20241231
```

### UGE Examples

```bash
# Export job data (last year by default)
./export_uge_comprehensive.sh
# Output: uge_jobs_with_users_YYYYMMDD.csv

# Export cluster configuration (REQUIRED)
./export_uge_cluster_config.sh
# Output: uge_cluster_config.csv

# Full year 2024
./export_uge_comprehensive.sh 01/01/2024 12/31/2024

# Just Q4
./export_uge_comprehensive.sh 10/01/2024 12/31/2024
```

### Anonymize for Sharing

```bash
# Anonymize job data (users, groups, nodelist)
./anonymize_cluster_data.sh \
  slurm_jobs_with_users_20260212.csv \
  jobs_anonymized.csv \
  mapping.txt

# Anonymize cluster config (hostnames)
./anonymize_cluster_data.sh \
  slurm_cluster_config.csv \
  cluster_anonymized.csv \
  mapping.txt

# Keep mapping.txt private! It contains user AND hostname mappings.
```

---

## Date Format Reference

Each scheduler requires dates in its native format:

| Scheduler | Date Format | Example | Notes |
|-----------|-------------|---------|-------|
| **SLURM** | `YYYY-MM-DD` | `2024-01-01` | ISO 8601 standard |
| **LSF** | `YYYY/MM/DD` | `2024/01/01` | Slashes required |
| **PBS/Torque** | `YYYYMMDD` | `20240101` | No separators |
| **UGE/SGE** | `MM/DD/YYYY` | `01/01/2024` | US date format |
| **HTCondor** | N/A | N/A | Uses all history |

**All scripts follow the same pattern:**
```bash
./export_script [START_DATE] [END_DATE]
```

Omit both arguments to use the default (last 1 year).

---

## Anonymization

The anonymization script creates deterministic mappings and works with **both job data and cluster config** files:

**Job Data - Before:**
```csv
user,group,account,job_id,nodelist,cpus
jsmith,research,proj_alpha,12345,node-gpu-01.hpc.edu,16
ajones,physics,proj_beta,12346,compute-a001.org,32
```

**Job Data - After:**
```csv
user,group,account,job_id,nodelist,cpus
user_0001,group_A,proj_alpha,12345,node_0001,16
user_0002,group_B,proj_beta,12346,node_0002,32
```

**Cluster Config - Before:**
```csv
hostname,cpus,memory_mb,gpus
node-gpu-01.hpc.university.edu,64,256000,2
compute-a001.cluster.org,48,192000,0
```

**Cluster Config - After:**
```csv
hostname,cpus,memory_mb,gpus
node_0001,64,256000,2
node_0002,48,192000,0
```

**Features:**
- **Three-way anonymization:** Users, groups, AND hostnames
- **Compatible:** Works with job data and cluster config exports from all schedulers
- **Deterministic:** Same user/hostname always gets same ID
- **Smart detection:** Automatically finds user/group/hostname columns
- **Preserves patterns:** Behavioral analysis still valid
- **Secure:** Original identities not recoverable without mapping file
- **Account preserved:** Project/billing identifiers kept intact

**What gets anonymized:**
- `user`, `username`, `uid` → `user_0001`, `user_0002`, ...
- `group`, `groupname`, `gid` → `group_A`, `group_B`, ...
- `hostname`, `nodename`, `nodelist` → `node_0001`, `node_0002`, ...

**Important:** Keep `mapping.txt` secure and private. It contains the key to re-identify users and hostnames.

---

## Troubleshooting

### SLURM: "sacct: command not found"
```bash
module load slurm  # or similar
which sacct        # verify it's available
```

### LSF: "User not authorized"
```bash
bhist -a  # Use -a flag for all users (requires admin)
```

### PBS: "Permission denied"
```bash
sudo ./export_pbs_comprehensive.sh ...  # PBS often requires sudo
```

### UGE: "qacct: unknown option"
```bash
# Check your UGE version
qacct -help
# Adjust script if needed for your version
```

### Export Takes Too Long
```bash
# Use shorter date ranges
./export_lsf_comprehensive.sh 2024/10/01 2024/10/31  # Just October

# Or compress output
./export_with_users.sh | gzip > output.csv.gz
```

### CSV Has Weird Characters
```bash
# Force UTF-8 encoding
export LC_ALL=en_US.UTF-8
./export_with_users.sh
```

---

## Auto-Detection Script

Don't know which scheduler you have?

```bash
./export_cluster_configs_all.sh
```

This will:
1. Detect your scheduler type
2. Run the appropriate export script
3. Standardize the output format

---

## Output File Locations

By default, scripts create timestamped files in the current directory:

```
slurm_jobs_with_users_YYYYMMDD.csv       # SLURM job export
slurm_cluster_config.csv                 # SLURM cluster config
lsf_jobs_comprehensive_YYYYMMDD.csv      # LSF job export
lsf_cluster_config.csv                   # LSF cluster config
pbs_jobs_with_users_YYYYMMDD.csv         # PBS job export
pbs_cluster_config.csv                   # PBS cluster config
uge_jobs_with_users_YYYYMMDD.csv         # UGE job export
uge_cluster_config.csv                   # UGE cluster config
htcondor_jobs.csv                        # HTCondor job export
htcondor_cluster_config.csv              # HTCondor cluster config
```

Where `YYYYMMDD` is the date the export was run (e.g., `20260206`).

---

## Security & Privacy

### Data Contains Sensitive Information

Job data may include:
- Usernames
- Group memberships
- Job submission patterns (can reveal research focus)
- Resource usage (can indicate project importance)

**Recommendations:**
1. **Anonymize before sharing** outside your organization
2. **Encrypt during transfer** (use scp, sftp, or encrypted email)
3. **Secure storage** (restricted access, encrypted at rest)
4. **Delete mapping files** after analysis if not needed
5. **Get institutional approval** before collecting data

### Anonymization is One-Way

Without the mapping file, anonymization cannot be reversed. This means:
- ✅ Safe to share anonymized data publicly
- ✅ Cannot re-identify users from anonymized data alone
- ⚠️ Keep mapping file secure if you need to re-identify later
- ⚠️ Lose mapping file = permanently anonymized

---

## Scheduler-Specific Notes

### SLURM

**Advantages:**
- Fast exports with `sacct`
- Comprehensive data available
- No special permissions usually needed

**Limitations:**
- Default retention period (often 30-90 days)
- May need to query slurmdbd directly for older data

**Tips:**
```bash
# Check retention period
sacct --starttime=2020-01-01 --endtime=2020-01-02 -X
# If this works, data goes back to 2020

# Export from specific partition
sacct -r partition_name ...
```

### IBM Spectrum LSF

**Advantages:**
- Rich job history via `bhist`
- Good backwards compatibility

**Limitations:**
- Requires `-a` flag for admin access to all users
- Date format specific (YYYY/MM/DD)
- Can be slow on large datasets

**Tips:**
```bash
# Test on small date range first
bhist -a -l 2024/12/01 2024/12/01 | head

# Run in background for large exports
nohup ./export_lsf_comprehensive.sh 2024/01/01 2024/12/31 &
```

### PBS/Torque/PBS Pro

**Advantages:**
- Detailed accounting logs
- Long retention (often years)

**Limitations:**
- Usually requires sudo for log access
- Log format varies by version
- Parsing can be slow

**Tips:**
```bash
# Check log location
ls -lh /var/spool/pbs/server_priv/accounting/

# If sudo required
sudo ./export_pbs_comprehensive.sh 20240101 20241231

# Or copy logs first (one-time sudo)
sudo cp -r /var/spool/pbs/server_priv/accounting/ ~/pbs_logs/
# Then modify script to read from ~/pbs_logs/
```

### UGE/SGE/OGE

**Advantages:**
- `qacct` provides structured output
- Usually no special permissions needed

**Limitations:**
- Date format specific (MM/DD/YYYY)
- May have gaps in data
- Different vendors have slight variations

**Tips:**
```bash
# Test qacct format
qacct -j 12345  # Query a known job

# Check available date range
qacct -b 01/01/2020 -e 01/02/2020

# Different UGE versions may need script adjustments
```

### HTCondor

**Advantages:**
- `condor_history` powerful query language
- Usually complete history available

**Limitations:**
- Output format complex
- May need multiple queries for all data

**Tips:**
```bash
# Check history size
condor_history -limit 10

# If history is huge, limit by time
condor_history -constraint 'JobStartDate >= 1704067200'  # Unix timestamp
```

---

## Data Format Standardization

If you have exports from multiple schedulers, use:

```bash
python3 standardize_cluster_config.py input_config.csv
```

This normalizes all scheduler-specific formats to a common structure.

---

## Example Workflow

**Complete workflow showing BOTH required exports:**

```bash
# 1. Export job data (historical submissions)
./export_with_users.sh
# Output: slurm_jobs_with_users_20260212.csv

# 2. Export cluster configuration (REQUIRED - separate step)
./export_slurm_cluster_config.sh
# Output: slurm_cluster_config.csv

# 3. Anonymize job data for sharing
./anonymize_cluster_data.sh \
  slurm_jobs_with_users_20260212.csv \
  jobs_anonymized.csv \
  mapping.txt

# 4. Share BOTH files (job data + cluster config)
# Keep mapping.txt private!
scp jobs_anonymized.csv remote:~/data/
scp slurm_cluster_config.csv remote:~/data/

# 5. Securely store mapping (optional)
gpg --encrypt --recipient you@example.com mapping.txt
rm mapping.txt  # Remove unencrypted version
```

**Why both files?**
- **Job data:** Workload patterns, user behavior, queue times
- **Cluster config:** Capacity, node types, partitions for context

---

## File Sizes

Expect approximately:

| Jobs | CSV Size (uncompressed) |
|------|-------------------------|
| 10,000 | ~2 MB |
| 100,000 | ~20 MB |
| 1,000,000 | ~200 MB |
| 10,000,000 | ~2 GB |

**Tip:** Compress large files:
```bash
gzip jobs_export.csv
# Result: jobs_export.csv.gz (typically 10-20% of original size)
```

---

## License

MIT License - Free to use, modify, and distribute.

---

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review your scheduler's documentation
3. Test with a small date range first
4. Check file permissions and command availability

---

## What's Not Included

This is a **data collection toolkit** only. It does NOT include:
- Analysis scripts
- Visualization tools
- Statistical analysis
- Machine learning models
- Cloud migration calculators

These scripts simply export raw data in a standardized format. You can then analyze the data with your preferred tools (Python, R, Excel, etc.).

---

## Contributing

Improvements welcome! Common enhancements:
- Additional scheduler support
- Better error handling
- Performance optimizations
- Additional output formats (JSON, Parquet, etc.)

---

## Version

Data Export Tools v2.0 - Simplified for data collection only.
