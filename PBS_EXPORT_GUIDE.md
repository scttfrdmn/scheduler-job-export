# PBS/Torque Data Export Guide

Complete guide for exporting and analyzing data from PBS Pro, Torque, and OpenPBS clusters.

## Quick Start

```bash
# 1. Export cluster configuration
./export_pbs_cluster_config.sh

# 2. Export job history (1 year)
sudo ./export_pbs_comprehensive.sh 20240101 20241231

# 3. Anonymize job data
./anonymize_cluster_data.sh \
  pbs_jobs_with_users_YYYYMMDD.csv \
  pbs_jobs_anonymized.csv \
  pbs_mapping_secure.txt

# 4. Analyze!
python3 analyze_concurrent_load.py
python3 analyze_submission_abandonment_events.py
```

## Scripts

### 1. export_pbs_comprehensive.sh

**Purpose:** Export complete job history with user/group information

**Usage:**
```bash
./export_pbs_comprehensive.sh [start_date] [end_date]

# Examples:
./export_pbs_comprehensive.sh                      # Last year
./export_pbs_comprehensive.sh 20240101 20241231   # Specific range
```

**Date format:** `YYYYMMDD`

**What it exports:**
- User and group information
- Job resources (CPUs, memory, nodes)
- Submit, start, and end times
- Queue information
- Exit codes
- Execution hosts

**Output:** `pbs_jobs_with_users_YYYYMMDD.csv`

**Requirements:**
- Read access to PBS accounting directory
- Typically requires root or PBS admin privileges
- PBS accounting must be enabled

### 2. export_pbs_cluster_config.sh

**Purpose:** Export cluster configuration (actual hardware inventory)

**Usage:**
```bash
./export_pbs_cluster_config.sh
```

**What it exports:**
- All nodes in the cluster
- CPUs per node
- Memory per node
- Node states (free, allocated, down)
- GPU nodes (if present)
- Node properties

**Output:** `pbs_cluster_config_YYYYMMDD.csv`

**Requirements:**
- Access to `pbsnodes` command
- Normal user privileges (no root needed)

## PBS Variants Supported

The scripts auto-detect and handle all major PBS variants:

| Variant | Common In | Notes |
|---------|-----------|-------|
| **PBS Pro** | National labs, commercial HPC | Most feature-rich |
| **Torque** | Universities, research clusters | Open source, legacy |
| **OpenPBS** | New installations | Open source, modern |

**Detection:** Scripts automatically detect variant from command output.

## PBS-Specific Notes

### Accounting Directory Locations

PBS stores accounting logs in different locations depending on installation:

**Common locations:**
```bash
# PBS Pro / Torque standard
/var/spool/pbs/server_priv/accounting/

# Torque alternate
/var/spool/torque/server_priv/accounting/

# PBS Pro alternate
/opt/pbs/server_priv/accounting/

# Custom
$PBS_HOME/server_priv/accounting/
```

**If non-standard location:**
```bash
export PBS_HOME=/custom/path/to/pbs
./export_pbs_comprehensive.sh 20240101 20241231
```

### Accounting File Format

PBS accounting files are named by date: `YYYYMMDD`

**Example:**
```bash
/var/spool/pbs/server_priv/accounting/
├── 20240101
├── 20240102
├── 20240103.gz   # Compressed
└── 20240104.bz2  # Compressed
```

**Script handles:**
- Plain text files
- Gzip compressed (.gz)
- Bzip2 compressed (.bz2)

### Accounting Record Format

PBS accounting format: **semicolon-delimited**

```
timestamp;record_type;job_id;key=value;key=value;...
```

**Record types:**
- `E` = End (completed job) - **we export these**
- `S` = Start
- `Q` = Queue
- `D` = Delete
- `A` = Abort

**Example:**
```
1704067200;E;12345.server;user=jsmith;group=physics;queue=batch;...
```

### Date Formats

**For export scripts:** `YYYYMMDD`

```bash
# Correct
./export_pbs_comprehensive.sh 20240101 20241231

# Wrong
./export_pbs_comprehensive.sh 2024-01-01 2024-12-31
./export_pbs_comprehensive.sh 01/01/2024 12/31/2024
```

**In accounting logs:** Epoch timestamps (seconds since 1970)
- Script automatically converts to ISO 8601: `YYYY-MM-DD HH:MM:SS`

### Resource Specifications

PBS has different resource formats for different variants:

#### PBS Pro Format
```
Resource_List.ncpus=32
Resource_List.mem=128gb
Resource_List.nodect=2
```

#### Torque Format
```
Resource_List.nodes=2:ppn=16
Resource_List.mem=128gb
```

**Script handles both:**
- Torque: `nodes=2:ppn=16` → CPUs = 32
- PBS Pro: `ncpus=32` → CPUs = 32
- Memory: Converts gb/mb/kb → MB

### Execution Hosts

PBS formats execution hosts as:

```
exec_host=node1/0+node1/1+node2/0+node2/1
```

Or with task counts:

```
exec_host=node1/0*8+node2/0*8
```

**Script extracts:**
- Unique hostnames: `node1,node2`
- Node count: `2`

### Node States

PBS node states:

| State | Meaning | Mapped To |
|-------|---------|-----------|
| `free` | Available | idle |
| `job-exclusive` | Running exclusive job | allocated |
| `job-sharing` | Running shared jobs | allocated |
| `busy` | High load | allocated |
| `down` | Not responding | down |
| `offline` | Administratively down | down |
| `state-unknown` | Unknown | unknown |

## Field Mapping

How PBS fields map to standard format:

| Standard Field | PBS Pro Source | Torque Source | Notes |
|----------------|----------------|---------------|-------|
| `user` | user | user | Username |
| `group` | group | group | Unix group |
| `account` | account | Account_Name | Account/project |
| `cpus` | Resource_List.ncpus | nodes * ppn | Cores requested |
| `mem_req` | Resource_List.mem | Resource_List.mem | MB |
| `nodes` | Resource_List.nodect | nodes count | Node count |
| `nodelist` | exec_host | exec_host | Comma-separated |
| `queue` | queue | queue | Queue name |
| `submit_time` | ctime | ctime | ISO 8601 |
| `start_time` | start | start | ISO 8601 |
| `end_time` | End record timestamp | End record timestamp | ISO 8601 |
| `exit_status` | Exit_status | Exit_status | Job exit code |

## Common Issues

### Issue: "Cannot find PBS accounting directory"

**Cause:** PBS installed in non-standard location

**Solution 1:** Set PBS_HOME
```bash
export PBS_HOME=/opt/pbs
./export_pbs_comprehensive.sh 20240101 20241231
```

**Solution 2:** Set accounting directory directly
```bash
export PBS_ACCT_DIR=/custom/path/to/accounting
./export_pbs_comprehensive.sh 20240101 20241231
```

**Solution 3:** Find it manually
```bash
# Find PBS directories
find /var /opt /usr -name accounting -type d 2>/dev/null | grep pbs

# Once found
export PBS_HOME=/path/to/pbs
```

### Issue: "Cannot read accounting directory"

**Cause:** Permission denied (accounting logs require root/PBS admin)

**Solution 1:** Run with sudo
```bash
sudo ./export_pbs_comprehensive.sh 20240101 20241231
```

**Solution 2:** Request PBS admin to run
```bash
# Admin runs as root or pbs user
sudo -u pbs ./export_pbs_comprehensive.sh 20240101 20241231
```

**Solution 3:** Copy files to accessible location
```bash
# As root
sudo cp /var/spool/pbs/server_priv/accounting/202401* /tmp/acct/
sudo chown $USER /tmp/acct/*
export PBS_ACCT_DIR=/tmp/acct
./export_pbs_comprehensive.sh 20240101 20241231
```

### Issue: "No accounting files found in date range"

**Cause:** Date range doesn't match available data

**Solution:** Check available files
```bash
# List accounting files
ls -l /var/spool/pbs/server_priv/accounting/

# Files are named YYYYMMDD
# Adjust date range to match available files
./export_pbs_comprehensive.sh 20231101 20231130
```

### Issue: "pbsnodes: command not found"

**Cause:** PBS not installed or not in PATH

**Solution 1:** Find PBS binaries
```bash
# Locate PBS installation
which qstat
ls -d /opt/pbs* /var/spool/pbs 2>/dev/null

# Add to PATH
export PATH=$PATH:/opt/pbs/bin
```

**Solution 2:** Source PBS profile
```bash
# PBS Pro
source /etc/profile.d/pbs.sh

# Or
source /opt/pbs/etc/pbs.sh
```

### Issue: Missing CPU or memory information

**Cause:** Jobs didn't specify resources, or using defaults

**Solution:** This is normal PBS behavior
- Jobs without explicit resource requests use queue defaults
- Script sets CPUs = 1 if not specified
- Memory may be empty if not requested
- Not a bug, just reflects how jobs were submitted

### Issue: Different PBS variant than expected

**Cause:** Multiple PBS installations or incorrect detection

**Solution:** Script auto-detects, but you can verify
```bash
# Check PBS variant
qstat --version  # PBS Pro
pbsnodes --version  # PBS Pro / Torque
pbs-server --version  # Check installed version

# Check which commands are available
which qstat pbsnodes qsub
```

## Verification

After export, verify the data:

```bash
# Check file exists and has data
ls -lh pbs_jobs_with_users_*.csv

# Count records
wc -l pbs_jobs_with_users_*.csv

# View header
head -1 pbs_jobs_with_users_*.csv

# View sample records
head -20 pbs_jobs_with_users_*.csv

# Check for critical fields
cut -d, -f1,4,11,12,13 pbs_jobs_with_users_*.csv | head -20
# Should show: user,job_id,submit_time,start_time,end_time

# Count unique users
cut -d, -f1 pbs_jobs_with_users_*.csv | sort -u | wc -l

# Count unique queues
cut -d, -f6 pbs_jobs_with_users_*.csv | sort -u | wc -l

# Check date range
cut -d, -f11 pbs_jobs_with_users_*.csv | sort -u | head -5
cut -d, -f11 pbs_jobs_with_users_*.csv | sort -u | tail -5
```

## Output Format

### Job Export CSV Columns

```
user          - Username who submitted job
group         - Unix group
account       - PBS account/project
job_id        - PBS job ID (e.g., 12345.server)
job_name      - Job name
queue         - PBS queue name
cpus          - CPUs requested
mem_req       - Memory requested (MB)
nodes         - Number of nodes requested
nodelist      - Comma-separated hostnames where job ran
submit_time   - When job was submitted (YYYY-MM-DD HH:MM:SS)
start_time    - When job started (YYYY-MM-DD HH:MM:SS)
end_time      - When job completed (YYYY-MM-DD HH:MM:SS)
exit_status   - Job exit code (0 = success)
```

### Cluster Config CSV Columns

```
hostname           - Node name
cpus               - Total CPUs/cores
memory_mb          - Total memory in MB
node_type          - compute, gpu, etc.
state              - Raw PBS state
state_simplified   - idle, allocated, down
gpus               - Number of GPUs (if applicable)
properties         - Node properties/features
```

## Anonymization

The job export is compatible with the standard anonymization script:

```bash
./anonymize_cluster_data.sh \
  pbs_jobs_with_users_20250129.csv \
  pbs_jobs_anonymized.csv \
  pbs_mapping_secure.txt
```

**What gets anonymized:**
- ✅ Usernames → user_0001, user_0002, ...
- ✅ Groups → group_A, group_B, ...
- ✅ Accounts/Projects → account_X, account_Y, ...

**What stays the same:**
- ✅ All timestamps
- ✅ All resource requests
- ✅ All queue information
- ✅ All usage patterns
- ✅ Node names (no user info)

**Security:**
```bash
# Secure the mapping file
chmod 600 pbs_mapping_secure.txt
sudo mv pbs_mapping_secure.txt /root/secure/

# Delete the original (with real usernames)
rm pbs_jobs_with_users_20250129.csv

# Keep only anonymized version
# Share: pbs_jobs_anonymized.csv ✓
# Keep private: pbs_mapping_secure.txt ✗
```

## Analysis

Once you have anonymized data, run the analysis:

### 1. Cluster Configuration Analysis

Shows actual cluster capacity:

```bash
python3 analyze_cluster_config.py pbs_cluster_config_20250129.csv
```

**Outputs:**
- Total nodes and CPUs
- CPU distribution
- Memory distribution
- Node states
- GPU nodes

### 2. Concurrent Load Analysis

Shows CPU utilization over time:

```bash
python3 analyze_concurrent_load.py
```

**Requires:** Anonymized job CSV

**Outputs:**
- Peak concurrent CPUs
- Mean concurrent CPUs
- Utilization time series
- Charts and graphs

### 3. Submission Abandonment Analysis

Tests if users avoid submitting during congestion:

```bash
python3 analyze_submission_abandonment_events.py
```

**Requires:** Anonymized job CSV

**Outputs:**
- Correlation between queue depth and submission rate
- Statistical significance
- Lag analysis
- Per-user behavior

### 4. True Utilization Calculation

Compare actual usage vs. capacity:

```bash
# From cluster config
Total Capacity: 13,920 CPUs (all nodes * CPUs per node)

# From concurrent load analysis
Peak Usage: 12,500 CPUs
Mean Usage: 7,800 CPUs

# Calculate
Peak Utilization: 12,500 / 13,920 = 89.8%
Mean Utilization: 7,800 / 13,920 = 56.0%
```

## Performance Tips

### Large Datasets

If you have millions of jobs:

1. **Export in chunks** (monthly)
```bash
for month in {01..12}; do
  ./export_pbs_comprehensive.sh 2024${month}01 2024${month}31
  mv pbs_jobs_with_users_*.csv pbs_2024_${month}.csv
done

# Combine later
cat pbs_2024_*.csv > pbs_2024_all.csv
```

2. **Process compressed files directly**
   - Script automatically handles .gz and .bz2

3. **Use fast storage**
   - Run on local SSD, not NFS

### Accounting File Management

PBS accounting files can grow large:

```bash
# Check sizes
du -sh /var/spool/pbs/server_priv/accounting/

# Compress old files
cd /var/spool/pbs/server_priv/accounting/
gzip 202301* 202302* 202303*

# Script still works with compressed files
```

## Multi-Site Collection

If collecting data from multiple PBS sites:

```bash
# Site 1
./export_pbs_comprehensive.sh 20240101 20241231
mv pbs_jobs_with_users_*.csv site1_pbs_jobs.csv
./anonymize_cluster_data.sh site1_pbs_jobs.csv site1_anon.csv site1_map.txt

# Site 2
./export_pbs_comprehensive.sh 20240101 20241231
mv pbs_jobs_with_users_*.csv site2_pbs_jobs.csv
./anonymize_cluster_data.sh site2_pbs_jobs.csv site2_anon.csv site2_map.txt

# Add cluster identifier
awk -F, 'NR==1{print $0",cluster"} NR>1{print $0",site1"}' site1_anon.csv > combined.csv
tail -n +2 site2_anon.csv | awk -F, '{print $0",site2"}' >> combined.csv

# Analyze combined
python3 analyze_submission_abandonment_events.py
```

## Troubleshooting Checklist

Before requesting help:

- [ ] PBS is installed (`which pbsnodes qstat`)
- [ ] Can access accounting directory (`ls /var/spool/pbs/server_priv/accounting/`)
- [ ] Date format is YYYYMMDD
- [ ] Have root/admin access for accounting logs
- [ ] Output CSV exists and has data (`wc -l`)
- [ ] All expected columns present (`head -1`)
- [ ] Timestamps in ISO 8601 format
- [ ] User and group columns populated

## Comparison: PBS vs SLURM

| Feature | PBS Command | SLURM Equivalent |
|---------|-------------|------------------|
| Job history | Accounting logs | `sacct` |
| Node list | `pbsnodes -a` | `sinfo` |
| Job status | `qstat` | `squeue` |
| Submit job | `qsub` | `sbatch` |
| Job details | `qstat -f` | `scontrol show job` |

**Key difference:** PBS uses flat accounting files, SLURM uses database.

## Additional Resources

- **PBS Documentation:** Check your PBS installation's docs
- **Anonymization Guide:** See `ANONYMIZATION_README.md`
- **Multi-Scheduler Guide:** See `MULTI_SCHEDULER_EXPORT_README.md`
- **Two-Part Export:** See `TWO_PART_EXPORT_GUIDE.md`
- **Complete Toolkit:** See `COMPLETE_TOOLKIT_SUMMARY.md`

## Support

### Altair PBS Pro
- Website: https://www.altair.com/pbs-works/
- Documentation: Usually in `/opt/pbs/doc/`

### Torque
- Website: http://www.adaptivecomputing.com/products/torque/
- Mailing list: torqueusers@supercluster.org

### OpenPBS
- Website: https://www.openpbs.org/
- GitHub: https://github.com/openpbs/openpbs

---

**Ready to export?** Run `./export_pbs_comprehensive.sh 20240101 20241231` to get started!
