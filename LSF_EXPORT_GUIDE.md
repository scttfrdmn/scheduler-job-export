# LSF Data Export Guide

Complete guide for exporting and analyzing data from IBM Spectrum LSF clusters.

## Quick Start

```bash
# 1. Export cluster configuration
./export_lsf_cluster_config.sh

# 2. Export job history (1 year)
./export_lsf_comprehensive.sh 2024/01/01 2024/12/31

# 3. Anonymize job data
./anonymize_cluster_data.sh \
  lsf_jobs_with_users_YYYYMMDD.csv \
  lsf_jobs_anonymized.csv \
  lsf_mapping_secure.txt

# 4. Analyze!
python3 analyze_concurrent_load.py
python3 analyze_submission_abandonment_events.py
```

## Scripts

### 1. export_lsf_comprehensive.sh

**Purpose:** Export complete job history with user/group information

**Usage:**
```bash
./export_lsf_comprehensive.sh [start_date] [end_date]

# Examples:
./export_lsf_comprehensive.sh                          # Last year
./export_lsf_comprehensive.sh 2024/01/01 2024/12/31  # Specific range
```

**Date format:** `YYYY/MM/DD`

**What it exports:**
- User and group information
- Job resources (CPUs, memory, nodes)
- Submit, start, and end times
- Queue and status information
- Exit codes

**Output:** `lsf_jobs_with_users_YYYYMMDD.csv`

**Requirements:**
- LSF environment must be sourced
- Access to `bhist` command
- Optional: `bacct` for enhanced resource data

### 2. export_lsf_cluster_config.sh

**Purpose:** Export cluster configuration (actual hardware inventory)

**Usage:**
```bash
./export_lsf_cluster_config.sh
```

**What it exports:**
- All hosts in the cluster
- CPUs per host
- Memory per host
- Host types and models
- Host status (ok, closed, unavailable)

**Output:** `lsf_cluster_config_YYYYMMDD.csv`

**Requirements:**
- Access to `bhosts` command
- Optional: `lshosts` for detailed hardware info

## LSF-Specific Notes

### Permissions

**For job data:**
- `bhist -a` requires LSF admin privileges (exports all users)
- Without `-a`, exports only your own jobs
- If you're a cluster admin, use `-a` for complete data

**For cluster config:**
- `bhosts` is available to all users
- `lshosts` is available to all users

### LSF Commands Used

| Command | Purpose | Privilege Required |
|---------|---------|-------------------|
| `bhist -l -a` | Detailed job history, all users | LSF admin (for `-a`) |
| `bhist -l` | Detailed job history, your jobs | Normal user |
| `bacct -l` | Accounting data with resource usage | Normal user |
| `bhosts -w` | Host list and status | Normal user |
| `bhosts -l` | Detailed host info | Normal user |
| `lshosts -w` | Hardware specifications | Normal user |

### Date Formats

LSF uses **YYYY/MM/DD** format:
```bash
# Correct
./export_lsf_comprehensive.sh 2024/01/01 2024/12/31

# Wrong
./export_lsf_comprehensive.sh 2024-01-01 2024-12-31
./export_lsf_comprehensive.sh 01/01/2024 12/31/2024
```

### Field Mapping

How LSF fields map to standard format:

| Standard Field | LSF Source | Notes |
|----------------|------------|-------|
| `user` | User from bhist | Username |
| `group` | User Group from bhist | Unix group |
| `account` | Project Name | LSF project |
| `cpus` | Processors Requested | Number of cores |
| `mem_req` | Requested Resources (rusage[mem=...]) | Memory in MB |
| `nodes` | Execution Hosts | Unique hostnames |
| `nodelist` | Execution Hosts | Comma-separated |
| `queue` | Queue | LSF queue name |
| `submit_time` | Submitted Time | ISO 8601 format |
| `start_time` | Started/Dispatched | ISO 8601 format |
| `end_time` | Completed/Finish Time | ISO 8601 format |
| `exit_status` | Exit Code | Job exit code |

## Common Issues

### Issue: "bhist: command not found"

**Cause:** LSF environment not loaded

**Solution:**
```bash
# Find LSF installation
ls -d /opt/lsf* /usr/local/lsf* 2>/dev/null

# Source LSF profile
source /opt/lsf/conf/profile.lsf

# Or add to your .bashrc
echo "source /opt/lsf/conf/profile.lsf" >> ~/.bashrc
```

### Issue: "bhist -a" fails with permission denied

**Cause:** Not an LSF administrator

**Solution 1:** Request admin to run export
```bash
# Admin runs:
sudo -u lsfadmin ./export_lsf_comprehensive.sh
```

**Solution 2:** Export only your jobs (remove `-a`)
```bash
# Edit export_lsf_comprehensive.sh, line ~52:
# Change: bhist -C "$START_DATE,${END_DATE}" -l -a
# To:     bhist -C "$START_DATE,${END_DATE}" -l
```

### Issue: "bacct: command not found"

**Cause:** `bacct` not installed or not in PATH

**Solution:** Script will fall back to `bhist` only (this is fine)

### Issue: Export is very slow

**Cause:** Large date range or many jobs

**Solution:** Export in smaller chunks
```bash
# Monthly exports
for month in {01..12}; do
  ./export_lsf_comprehensive.sh 2024/${month}/01 2024/${month}/31
done

# Then combine the CSV files
```

### Issue: Missing memory or CPU information

**Cause:** Jobs didn't specify resources, or LSF not configured to track

**Solution:**
- Memory: Some LSF jobs don't request memory explicitly
- CPUs: Should always be present; defaults to 1 if missing
- This is normal LSF behavior, not a bug in the script

## Verification

After export, verify the data:

```bash
# Check file size
ls -lh lsf_jobs_with_users_*.csv

# Count records
wc -l lsf_jobs_with_users_*.csv

# Check unique users
cut -d, -f1 lsf_jobs_with_users_*.csv | sort -u | wc -l

# View sample
head -20 lsf_jobs_with_users_*.csv

# Check for missing critical fields
cut -d, -f1,4,11,12,13 lsf_jobs_with_users_*.csv | head -20
# Should show: user,job_id,submit_time,start_time,end_time
```

## Output Format

### Job Export CSV Columns

```
user          - Username who submitted job
group         - Unix group
account       - LSF project name
job_id        - LSF job ID
job_name      - Job name
queue         - LSF queue name
cpus          - CPUs requested
mem_req       - Memory requested (MB)
nodes         - Number of execution hosts
nodelist      - Comma-separated hostnames
submit_time   - When job was submitted (YYYY-MM-DD HH:MM:SS)
start_time    - When job started (YYYY-MM-DD HH:MM:SS)
end_time      - When job completed (YYYY-MM-DD HH:MM:SS)
exit_status   - Job exit code
status        - LSF job status (DONE, EXIT, etc.)
```

### Cluster Config CSV Columns

```
hostname      - Host/server name
status        - LSF status (ok, closed, unavail)
cpus          - Total CPUs/cores
ncores        - Physical cores
nthreads      - Threads per core
memory_mb     - Total memory in MB
max_slots     - Maximum job slots
type          - OS/architecture type
model         - CPU model
```

## Anonymization

The job export is compatible with the standard anonymization script:

```bash
./anonymize_cluster_data.sh \
  lsf_jobs_with_users_20250129.csv \
  lsf_jobs_anonymized.csv \
  lsf_mapping_secure.txt
```

**What gets anonymized:**
- ✅ Usernames → user_0001, user_0002, ...
- ✅ Groups → group_A, group_B, ...
- ✅ Accounts/Projects → account_X, account_Y, ...

**What stays the same:**
- ✅ All timestamps (submit, start, end)
- ✅ All resource requests (CPUs, memory)
- ✅ All queue information
- ✅ All usage patterns

**Security:**
```bash
# Secure the mapping file
chmod 600 lsf_mapping_secure.txt
sudo mv lsf_mapping_secure.txt /root/secure/

# Delete the original (with real usernames)
rm lsf_jobs_with_users_20250129.csv

# Keep only the anonymized version
# Share: lsf_jobs_anonymized.csv ✓
# Keep private: lsf_mapping_secure.txt ✗
```

## Analysis

Once you have anonymized data, run the analysis:

### 1. Concurrent Load Analysis

Shows CPU utilization over time:

```bash
python3 analyze_concurrent_load.py
```

**Requires:** Anonymized job CSV

**Outputs:**
- Peak concurrent CPUs
- Mean concurrent CPUs
- Utilization charts
- Time series graphs

### 2. Submission Abandonment Analysis

Tests if users avoid submitting during congestion:

```bash
python3 analyze_submission_abandonment_events.py
```

**Requires:** Anonymized job CSV

**Outputs:**
- Correlation between queue depth and submission rate
- Statistical significance tests
- Lag analysis (how far back do users look?)
- Per-user behavior patterns

### 3. Cluster Utilization

Compare actual usage vs. capacity:

```bash
# First, analyze cluster config
python3 analyze_cluster_config.py lsf_cluster_config_20250129.csv

# Then compare with job data
# Peak usage from concurrent load analysis / Total capacity from config
```

## Multi-Site Collection

If collecting data from multiple LSF sites:

```bash
# Site 1
./export_lsf_comprehensive.sh 2024/01/01 2024/12/31
mv lsf_jobs_with_users_*.csv site1_lsf_jobs.csv
./anonymize_cluster_data.sh site1_lsf_jobs.csv site1_anon.csv site1_map.txt

# Site 2
./export_lsf_comprehensive.sh 2024/01/01 2024/12/31
mv lsf_jobs_with_users_*.csv site2_lsf_jobs.csv
./anonymize_cluster_data.sh site2_lsf_jobs.csv site2_anon.csv site2_map.txt

# Combine for cross-site analysis
# Add cluster identifier column
awk -F, 'NR==1{print $0",cluster"} NR>1{print $0",site1"}' site1_anon.csv > combined.csv
tail -n +2 site2_anon.csv | awk -F, '{print $0",site2"}' >> combined.csv

# Analyze combined dataset
python3 analyze_submission_abandonment_events.py
```

## Performance Tips

### Large Datasets

If you have millions of jobs:

1. **Export in chunks** (monthly or quarterly)
2. **Use bacct instead of bhist** (faster for accounting data)
3. **Filter by queue** if only analyzing specific workloads
4. **Run during off-hours** to avoid impacting LSF performance

### Memory Issues

If Python runs out of memory:

1. **Process in chunks** (modify analysis scripts)
2. **Increase system swap space**
3. **Use a larger machine** for analysis
4. **Sample the data** (every Nth job) for exploratory analysis

## Troubleshooting Checklist

- [ ] LSF environment sourced (`source /path/to/lsf/conf/profile.lsf`)
- [ ] Can run `bhist` command
- [ ] Can run `bhosts` command
- [ ] Date format is YYYY/MM/DD
- [ ] Have admin access (for `-a` flag) or removed `-a` from script
- [ ] Output CSV has data in it (`wc -l`)
- [ ] All expected columns present (`head -1`)
- [ ] Timestamps are in ISO 8601 format
- [ ] User and group columns exist (required for anonymization)

## Support

If you encounter issues:

1. **Check LSF version:** `lsid`
2. **Check available commands:** `which bhist bhosts lshosts bacct`
3. **Test manually:** `bhist -n 10` (should show last 10 jobs)
4. **Check LSF docs:** `bhist -h` or `man bhist`
5. **Review script output:** Look for Python errors in parsing

## Comparison: LSF vs SLURM

| Feature | LSF Command | SLURM Equivalent |
|---------|-------------|------------------|
| Job history | `bhist` | `sacct` |
| Accounting | `bacct` | `sacct` |
| Host list | `bhosts` | `sinfo` |
| Host details | `lshosts` | `sinfo -N` |
| Queue info | `bqueues` | `squeue` |
| Job details | `bjobs -l` | `scontrol show job` |

**Key difference:** LSF uses multiple commands for different data, while SLURM uses `sacct` for everything.

## Additional Resources

- **LSF Documentation:** Check your LSF installation's docs
- **Anonymization Guide:** See `ANONYMIZATION_README.md`
- **Multi-Scheduler Guide:** See `MULTI_SCHEDULER_EXPORT_README.md`
- **Two-Part Export:** See `TWO_PART_EXPORT_GUIDE.md`

---

**Ready to export?** Run `./export_lsf_comprehensive.sh` to get started!
