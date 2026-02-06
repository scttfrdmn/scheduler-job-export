# UGE/SGE Data Export Guide

Complete guide for exporting and analyzing data from Univa Grid Engine (UGE), Sun Grid Engine (SGE), and Open Grid Engine (OGE) clusters.

## Quick Start

```bash
# 1. Export cluster configuration
./export_uge_cluster_config.sh

# 2. Export job history (1 year)
./export_uge_comprehensive.sh 01/01/2024 12/31/2024

# 3. Anonymize job data
./anonymize_cluster_data.sh \
  uge_jobs_with_users_YYYYMMDD.csv \
  uge_jobs_anonymized.csv \
  uge_mapping_secure.txt

# 4. Analyze!
python3 analyze_concurrent_load.py
python3 analyze_submission_abandonment_events.py
```

## Scripts

### 1. export_uge_comprehensive.sh

**Purpose:** Export complete job history with user/group information

**Usage:**
```bash
./export_uge_comprehensive.sh [start_date] [end_date]

# Examples:
./export_uge_comprehensive.sh                          # Last year
./export_uge_comprehensive.sh 01/01/2024 12/31/2024   # Specific range
```

**Date format:** `MM/DD/YYYY` ⚠️ **UNIQUE TO UGE/SGE!**

**What it exports:**
- User and group information
- Job resources (slots/CPUs, memory)
- Submit, start, and end times
- Queue information
- Exit codes
- Execution hosts

**Output:** `uge_jobs_with_users_YYYYMMDD.csv`

**Requirements:**
- Access to `qacct` command
- SGE_ROOT environment variable set
- Grid Engine accounting enabled

### 2. export_uge_cluster_config.sh

**Purpose:** Export cluster configuration (actual hardware inventory)

**Usage:**
```bash
./export_uge_cluster_config.sh
```

**What it exports:**
- All execution hosts in the cluster
- CPUs/slots per host
- Memory per host
- Architecture information
- Load averages

**Output:** `uge_cluster_config_YYYYMMDD.csv`

**Requirements:**
- Access to `qhost` command
- SGE_ROOT environment variable set
- Normal user privileges

## UGE/SGE Variants Supported

The scripts auto-detect and handle all major Grid Engine variants:

| Variant | Common In | Status | Notes |
|---------|-----------|--------|-------|
| **Univa Grid Engine (UGE)** | Commercial, enterprises | Active | Most feature-rich |
| **Sun Grid Engine (SGE)** | Legacy Oracle | EOL | Still widely used |
| **Open Grid Engine (OGE)** | Open source | Community | SGE fork |
| **Son of Grid Engine** | Universities | Community | SGE fork |

**Detection:** Scripts automatically detect variant from command output.

## UGE/SGE-Specific Notes

### Environment Setup

Grid Engine requires environment variables:

```bash
# Check if already set
echo $SGE_ROOT
echo $SGE_CELL

# If not set, source settings file
source $SGE_ROOT/default/common/settings.sh

# Common locations for SGE_ROOT:
# /opt/sge
# /opt/uge
# /usr/local/sge
# /gridware/sge
```

**Add to .bashrc for persistence:**
```bash
echo "source /opt/sge/default/common/settings.sh" >> ~/.bashrc
```

### Date Format - IMPORTANT!

⚠️ **UGE/SGE uses MM/DD/YYYY - different from all other schedulers!**

```bash
# Correct for UGE/SGE
./export_uge_comprehensive.sh 01/01/2024 12/31/2024

# Wrong (this is SLURM/LSF format)
./export_uge_comprehensive.sh 2024/01/01 2024/12/31

# Wrong (this is PBS format)
./export_uge_comprehensive.sh 20240101 20241231
```

**Why different?** Historical Sun Microsystems convention.

### Accounting File

Grid Engine stores accounting in:

```bash
$SGE_ROOT/default/common/accounting
```

**Example:**
```bash
/opt/sge/default/common/accounting
```

**Format:** Plain text, colon-delimited records

**Permissions:** Usually readable by all users (unlike PBS which requires root)

### qacct Command

`qacct` queries the accounting database:

```bash
# Query by date range
qacct -b 01/01/2024 -e 12/31/2024

# Query specific user
qacct -u username

# Query specific job
qacct -j 12345
```

**Output format:** Text paragraphs separated by `====` lines

**Example:**
```
==============================================================
qname        batch.q
hostname     node1.cluster
group        physics
owner        jsmith
project      NONE
department   defaultdepartment
jobname      test_job
jobnumber    12345
...
==============================================================
```

### Resource Specifications

#### Slots (CPUs)

Grid Engine uses "slots" instead of "CPUs":

```
slots        32
```

**Our mapping:** slots = CPUs

#### Memory

Memory can be specified in different formats:

```
maxvmem      8.000G      # Gigabytes
maxvmem      8192.000M   # Megabytes
maxvmem      8388608.000K # Kilobytes
```

**Script converts all to MB**

#### Parallel Environments

For parallel jobs:

```
pe_taskid    MASTER      # Master task
pe_taskid    undefined   # Not a parallel job
```

#### Array Jobs

For array jobs:

```
jobnumber    12345
taskid       1          # Array task ID
```

**Job ID becomes:** `12345.1`

### Queue Names

Grid Engine queues (queue instances):

```
qname        batch.q@node1
```

**Format:** `queue_name.q@hostname`

**Script extracts:** `batch.q`

### Execution Hosts

Simple format:

```
hostname     node1.cluster.local
```

**Unlike PBS:** One hostname per job (not multi-node format)

**For parallel jobs:** Jobs may run on multiple hosts but qacct shows primary host

## Field Mapping

How UGE/SGE fields map to standard format:

| Standard Field | UGE/SGE Source | Notes |
|----------------|----------------|-------|
| `user` | owner | Username |
| `group` | group | Unix group |
| `account` | project | Project name |
| `cpus` | slots | Slots = CPUs |
| `mem_req` | maxvmem | Max virtual memory (MB) |
| `nodes` | 1 | UGE jobs typically single node |
| `nodelist` | hostname | Primary execution host |
| `queue` | qname | Queue name |
| `submit_time` | submission_time | ISO 8601 format |
| `start_time` | start_time | ISO 8601 format |
| `end_time` | end_time | ISO 8601 format |
| `exit_status` | failed or exit_status | 0 = success |

### Date Format Conversion

**UGE/SGE native format:**
```
submission_time  Mon Jan  1 00:00:00 2024
```

**Script converts to ISO 8601:**
```
2024-01-01 00:00:00
```

## Common Issues

### Issue: "qacct: command not found"

**Cause:** Grid Engine environment not loaded

**Solution 1:** Source settings file
```bash
# Find SGE_ROOT
ls -d /opt/sge* /opt/uge* /usr/local/sge* 2>/dev/null

# Source settings
source /opt/sge/default/common/settings.sh

# Verify
which qacct qhost qconf
echo $SGE_ROOT
```

**Solution 2:** Add to .bashrc
```bash
echo "source /opt/sge/default/common/settings.sh" >> ~/.bashrc
source ~/.bashrc
```

**Solution 3:** Manual PATH setup
```bash
export SGE_ROOT=/opt/sge
export SGE_CELL=default
export PATH=$SGE_ROOT/bin/linux-x64:$PATH
```

### Issue: "error: commlib error: access denied"

**Cause:** Grid Engine not properly configured for your user

**Solution:** Contact Grid Engine administrator
- User may need to be added to Grid Engine users list
- Check: `qconf -suserl`

### Issue: Wrong date format error

**Cause:** Using SLURM/LSF date format instead of UGE format

**Solution:** Use MM/DD/YYYY format
```bash
# Wrong
./export_uge_comprehensive.sh 2024/01/01 2024/12/31

# Correct
./export_uge_comprehensive.sh 01/01/2024 12/31/2024
```

### Issue: "qacct: no accounting file found"

**Cause:** Accounting not enabled or file moved

**Solution 1:** Check accounting file
```bash
# Default location
ls -l $SGE_ROOT/default/common/accounting

# Check SGE configuration
qconf -sconf | grep accounting
```

**Solution 2:** Enable accounting (requires admin)
```bash
# As SGE admin
qconf -mconf
# Set: accounting_flush_time and accounting_summary
```

### Issue: "qhost: no information available"

**Cause:** No execution hosts or qmaster not running

**Solution 1:** Check qmaster status
```bash
# Check if qmaster is running
qconf -ss
qconf -sds

# Start qmaster (requires admin)
$SGE_ROOT/default/common/sgemaster start
```

**Solution 2:** Check execution hosts
```bash
# List configured hosts
qconf -sel

# Check host status
qhost -q
```

### Issue: Missing memory information

**Cause:** Jobs didn't reach memory limit, so maxvmem not recorded

**Solution:** This is normal UGE/SGE behavior
- maxvmem only recorded if job uses significant memory
- ru_maxrss used as fallback
- Some jobs legitimately have no memory tracking
- Not a script bug

### Issue: Slow qacct queries

**Cause:** Large accounting file or long date range

**Solution 1:** Query in smaller chunks
```bash
# Monthly exports
for month in {01..12}; do
  ./export_uge_comprehensive.sh ${month}/01/2024 ${month}/31/2024
done
```

**Solution 2:** Query specific users (if testing)
```bash
# Edit script to add -u flag
qacct -b 01/01/2024 -e 12/31/2024 -u specific_user
```

## Verification

After export, verify the data:

```bash
# Check file exists and has data
ls -lh uge_jobs_with_users_*.csv

# Count records
wc -l uge_jobs_with_users_*.csv

# View header
head -1 uge_jobs_with_users_*.csv

# View sample records
head -20 uge_jobs_with_users_*.csv

# Check for critical fields
cut -d, -f1,4,11,12,13 uge_jobs_with_users_*.csv | head -20
# Should show: user,job_id,submit_time,start_time,end_time

# Count unique users
cut -d, -f1 uge_jobs_with_users_*.csv | sort -u | wc -l

# Count unique queues
cut -d, -f6 uge_jobs_with_users_*.csv | sort -u

# Check date range
cut -d, -f11 uge_jobs_with_users_*.csv | sort | head -5
cut -d, -f11 uge_jobs_with_users_*.csv | sort | tail -5
```

## Output Format

### Job Export CSV Columns

```
user          - Username (from 'owner' field)
group         - Unix group
account       - Project name
job_id        - Job number (with task ID if array job)
job_name      - Job name
queue         - Queue name
cpus          - Slots requested
mem_req       - Maximum virtual memory (MB)
nodes         - Number of nodes (typically 1)
nodelist      - Hostname where job ran
submit_time   - When job was submitted (YYYY-MM-DD HH:MM:SS)
start_time    - When job started (YYYY-MM-DD HH:MM:SS)
end_time      - When job completed (YYYY-MM-DD HH:MM:SS)
exit_status   - Job exit code (0 = success)
```

### Cluster Config CSV Columns

```
hostname       - Execution host name
num_proc       - Number of processors
mem_total_mb   - Total memory in MB
slots_total    - Total slots (= CPUs)
arch           - Architecture (lx-amd64, etc.)
load_avg       - Current load average
```

## Anonymization

The job export is compatible with the standard anonymization script:

```bash
./anonymize_cluster_data.sh \
  uge_jobs_with_users_20250129.csv \
  uge_jobs_anonymized.csv \
  uge_mapping_secure.txt
```

**What gets anonymized:**
- ✅ Usernames → user_0001, user_0002, ...
- ✅ Groups → group_A, group_B, ...
- ✅ Projects → account_X, account_Y, ...

**What stays the same:**
- ✅ All timestamps
- ✅ All resource requests
- ✅ All queue information
- ✅ All usage patterns
- ✅ Hostnames (no user info)

**Security:**
```bash
# Secure the mapping file
chmod 600 uge_mapping_secure.txt
sudo mv uge_mapping_secure.txt /root/secure/

# Delete the original
rm uge_jobs_with_users_20250129.csv

# Share only anonymized version
# Share: uge_jobs_anonymized.csv ✓
# Keep private: uge_mapping_secure.txt ✗
```

## Analysis

Once you have anonymized data:

### 1. Cluster Configuration Analysis

```bash
python3 analyze_cluster_config.py uge_cluster_config_20250129.csv
```

**Outputs:**
- Total execution hosts
- Total slots (CPUs)
- Memory capacity
- Architecture types

### 2. Concurrent Load Analysis

```bash
python3 analyze_concurrent_load.py
```

**Outputs:**
- Peak concurrent slots
- Mean concurrent slots
- Utilization over time

### 3. Submission Abandonment Analysis

```bash
python3 analyze_submission_abandonment_events.py
```

**Tests:** Do users avoid submitting when queue is long?

### 4. True Utilization

```bash
# From cluster config
Total Slots: 1,024 (from all execution hosts)

# From concurrent load
Peak Usage: 980 slots
Mean Usage: 650 slots

# Calculate
Peak Utilization: 980 / 1,024 = 95.7%
Mean Utilization: 650 / 1,024 = 63.5%
```

## Performance Tips

### Large Accounting Files

Grid Engine accounting can grow very large:

```bash
# Check size
du -sh $SGE_ROOT/default/common/accounting

# If very large, query in chunks
for month in {01..12}; do
  ./export_uge_comprehensive.sh ${month}/01/2024 ${month}/31/2024
  mv uge_jobs_with_users_*.csv uge_2024_${month}.csv
done

# Combine later
head -1 uge_2024_01.csv > uge_2024_all.csv
for f in uge_2024_*.csv; do
  tail -n +2 $f >> uge_2024_all.csv
done
```

### qacct Performance

For faster queries:

1. **Use specific user** (if testing)
   ```bash
   qacct -b 01/01/2024 -e 12/31/2024 -u testuser
   ```

2. **Query specific job range**
   ```bash
   qacct -j 10000-20000
   ```

3. **Run during off-peak hours**
   - qacct can impact qmaster performance

## Grid Engine Concepts

### Slots vs CPUs

**Slots** = schedulable units (typically = CPUs, but configurable)

```bash
# Check slot configuration
qconf -se <hostname>

# Slots can be set to:
# - Physical CPUs
# - Physical cores
# - Logical CPUs (with hyperthreading)
# - Arbitrary number
```

### Queue Instances

Grid Engine queues are templates; queue instances are per-host:

```bash
# Queue: batch.q
# Instances: batch.q@node1, batch.q@node2, ...

# List queue instances
qstat -f -q batch.q
```

### Parallel Environments (PE)

For parallel jobs (MPI, OpenMP):

```bash
# List parallel environments
qconf -spl

# Show PE details
qconf -sp mpi
```

**In accounting:**
- Jobs using PE have pe_taskid
- Master task: pe_taskid=MASTER
- Worker tasks may not appear in accounting

### Array Jobs

Submit many similar jobs:

```bash
# Submit array job
qsub -t 1-100 job.sh

# Creates jobs: 12345.1, 12345.2, ..., 12345.100
```

**In accounting:** Each task is separate record

## Multi-Site Collection

Collecting from multiple UGE/SGE sites:

```bash
# Site 1
./export_uge_comprehensive.sh 01/01/2024 12/31/2024
mv uge_jobs_with_users_*.csv site1_uge_jobs.csv
./anonymize_cluster_data.sh site1_uge_jobs.csv site1_anon.csv site1_map.txt

# Site 2
./export_uge_comprehensive.sh 01/01/2024 12/31/2024
mv uge_jobs_with_users_*.csv site2_uge_jobs.csv
./anonymize_cluster_data.sh site2_uge_jobs.csv site2_anon.csv site2_map.txt

# Combine
awk -F, 'NR==1{print $0",cluster"} NR>1{print $0",site1"}' site1_anon.csv > combined.csv
tail -n +2 site2_anon.csv | awk -F, '{print $0",site2"}' >> combined.csv

# Analyze
python3 analyze_submission_abandonment_events.py
```

## Troubleshooting Checklist

Before requesting help:

- [ ] Grid Engine installed (`which qacct qhost`)
- [ ] Environment sourced (`echo $SGE_ROOT`)
- [ ] Date format is MM/DD/YYYY
- [ ] qacct can query accounting (`qacct -j` works)
- [ ] Output CSV exists (`ls -l uge_jobs_with_users_*.csv`)
- [ ] CSV has data (`wc -l`)
- [ ] Header row present (`head -1`)
- [ ] User/group columns populated

## Comparison: UGE/SGE vs SLURM

| Feature | UGE/SGE Command | SLURM Equivalent |
|---------|-----------------|------------------|
| Job history | `qacct` | `sacct` |
| Host list | `qhost` | `sinfo` |
| Job status | `qstat` | `squeue` |
| Submit job | `qsub` | `sbatch` |
| Job details | `qstat -j` | `scontrol show job` |
| Configuration | `qconf` | `scontrol show config` |

**Key differences:**
- UGE/SGE: Text file accounting, requires parsing
- SLURM: Database accounting, CSV output

## Additional Resources

- **Anonymization:** See `ANONYMIZATION_README.md`
- **Multi-Scheduler:** See `MULTI_SCHEDULER_EXPORT_README.md`
- **Two-Part Export:** See `TWO_PART_EXPORT_GUIDE.md`
- **Complete Toolkit:** See `COMPLETE_TOOLKIT_SUMMARY.md`

### Vendor Resources

**Univa Grid Engine:**
- Website: http://www.univa.com/products/
- Documentation: Usually in `$SGE_ROOT/doc/`

**Open Grid Engine:**
- Website: http://gridscheduler.sourceforge.net/
- Mailing list: users@gridengine.sunsource.net

**Son of Grid Engine:**
- Website: https://arc.liv.ac.uk/trac/SGE
- GitHub: https://github.com/daimh/sge

## Grid Engine Commands Quick Reference

```bash
# Environment
source $SGE_ROOT/default/common/settings.sh

# Job accounting
qacct -b 01/01/2024 -e 12/31/2024        # Date range
qacct -u username                         # Specific user
qacct -j 12345                            # Specific job

# Host information
qhost                                     # List hosts
qhost -F                                  # Detailed info
qhost -xml                                # XML output
qhost -q                                  # Queue instances

# Configuration
qconf -sel                                # List execution hosts
qconf -sql                                # List queues
qconf -spl                                # List parallel environments
qconf -suserl                             # List users

# Status
qstat                                     # Job status
qstat -f                                  # Full status
qstat -u '*'                              # All users
```

---

**Ready to export?** Remember the date format: `./export_uge_comprehensive.sh 01/01/2024 12/31/2024` 📅
