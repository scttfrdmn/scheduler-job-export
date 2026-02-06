# Multi-Scheduler Job Data Export & Anonymization

This toolkit supports exporting and anonymizing job data from **all major HPC schedulers**. All export scripts produce compatible CSV output that works with the same anonymization script.

## Supported Schedulers

| Scheduler | Script | Command | Status |
|-----------|--------|---------|--------|
| **SLURM** | `export_with_users.sh` | `sacct` | ✅ Tested |
| **UGE/SGE/OGE** | `export_uge_data.sh` | `qacct` | ✅ Ready |
| **PBS/Torque/PBS Pro** | `export_pbs_data.sh` | `bhist` / acct logs | ✅ Ready |
| **IBM Spectrum LSF** | `export_lsf_data.sh` | `bhist` | ✅ Ready |
| **HTCondor** | `export_htcondor_data.sh` | `condor_history` | ✅ Ready |

## Quick Start

### 1. Export Job Data (Pick Your Scheduler)

**SLURM:**
```bash
./export_with_users.sh
```

**UGE/SGE:**
```bash
./export_uge_data.sh 01/01/2024 12/31/2024
```

**PBS/Torque:**
```bash
./export_pbs_data.sh 20240101 20241231
```

**LSF:**
```bash
./export_lsf_data.sh 2024/01/01 2024/12/31
```

**HTCondor:**
```bash
./export_htcondor_data.sh 365  # Last 365 days
```

### 2. Anonymize (Same Script for All Schedulers!)

```bash
./anonymize_cluster_data.sh \
  <scheduler>_jobs_with_users_YYYYMMDD.csv \
  <scheduler>_jobs_anonymized.csv \
  mapping_secure.txt
```

### 3. Secure Mapping File

```bash
chmod 600 mapping_secure.txt
sudo mv mapping_secure.txt /root/secure/
```

### 4. Analyze!

Now you can run submission abandonment analysis or any other analysis on the anonymized data.

## Output Format

All export scripts produce CSV with these standard columns:

| Column | Description |
|--------|-------------|
| `user` | Username |
| `group` | Unix group or department |
| `account` | Account/project name |
| `job_id` | Unique job identifier |
| `job_name` | Job name (if available) |
| `queue` | Queue/partition name |
| `cpus` | CPUs requested |
| `mem_req` | Memory requested |
| `nodes` | Number of nodes |
| `nodelist` | Comma-separated node names |
| `submit_time` | When job was submitted (ISO 8601) |
| `start_time` | When job started running (ISO 8601) |
| `end_time` | When job completed (ISO 8601) |
| `exit_status` | Job exit code |

**Note:** Some schedulers may not have all fields. Missing fields are left empty.

## Scheduler-Specific Notes

### SLURM

**Command:** `sacct`

**Date format:** ISO dates (2024-01-01)

**Special notes:**
- Native support for all fields
- Can export very large datasets efficiently
- Use `--starttime` and `--endtime` for date ranges

**Example:**
```bash
./export_with_users.sh
# Or manually:
sacct -a \
  --format=User,Account,Group,JobID,JobName,Partition,ReqCPUS,ReqMem,NNodes,NodeList,AllocTRES,ReqGRES,Submit,Start,End,State \
  --starttime 2024-01-01 \
  --parsable2 \
  > slurm_jobs.csv
```

### UGE/SGE/OGE (Univa/Sun/Open Grid Engine)

**Command:** `qacct`

**Date format:** MM/DD/YYYY

**Special notes:**
- Queries accounting database directly
- Output is text format (script parses to CSV)
- May be slow for large date ranges
- Group info from `group` field

**Example:**
```bash
./export_uge_data.sh 01/01/2024 12/31/2024
```

**Permissions required:**
- Read access to accounting database
- May need to be SGE admin or in appropriate group

### PBS/Torque/PBS Pro

**Command:** Accounting log files + optional `tracejob`

**Date format:** YYYYMMDD

**Special notes:**
- Reads accounting logs from `/var/spool/pbs/server_priv/accounting/`
- Or `/var/spool/pbs/server_logs/` for PBS Pro
- Parses semicolon-delimited accounting format
- Looks for 'E' (End) records for completed jobs

**Example:**
```bash
./export_pbs_data.sh 20240101 20241231
```

**Permissions required:**
- Read access to PBS accounting directory
- May need root or pbs admin privileges

**Troubleshooting:**
If accounting directory is non-standard:
```bash
export PBS_ACCT_DIR=/custom/path/to/accounting
./export_pbs_data.sh 20240101 20241231
```

### IBM Spectrum LSF

**Command:** `bhist`

**Date format:** YYYY/MM/DD

**Special notes:**
- Uses `bhist -l` for detailed output
- May be very slow for large date ranges
- Consider limiting to recent months first
- Group from "User Group" field

**Example:**
```bash
./export_lsf_data.sh 2024/01/01 2024/12/31
```

**Permissions required:**
- LSF user account
- Read access to LSF accounting database

**Performance tips:**
- For large datasets, export in monthly chunks
- Use `-u <username>` to export specific users first

### HTCondor

**Command:** `condor_history`

**Date format:** Days ago (integer)

**Special notes:**
- Queries HTCondor history database
- Group info extracted from AcctGroup or AccountingGroup
- Format: "group.username" → extracts "group"
- May need `-file` option if using file-based history

**Example:**
```bash
./export_htcondor_data.sh 365  # Last 365 days
```

**Permissions required:**
- HTCondor user account
- Access to history database

**Troubleshooting:**
If using file-based history:
```bash
# Edit script to add -file option:
condor_history -file /path/to/history ...
```

## Anonymization

The `anonymize_cluster_data.sh` script works with ALL scheduler exports:

**What it does:**
- Auto-detects user/group columns
- Creates deterministic mappings:
  - `jsmith` → `user_0001`
  - `physics` → `group_A`
- Preserves all usage patterns
- Creates secure mapping file

**What it preserves:**
- ✅ Per-user resource usage
- ✅ Per-group patterns
- ✅ Temporal patterns
- ✅ Job sizes and runtimes
- ✅ Queue behavior

**What it protects:**
- ❌ Real usernames
- ❌ Real group names
- ❌ Personal identities

## Analysis Scripts

Once you have anonymized data, you can run:

**Submission Abandonment Analysis:**
```bash
python3 analyze_submission_abandonment_events.py
```

**Basic Statistics:**
```bash
python3 analyze_jobs.py
```

**Utilization Analysis:**
```bash
python3 analyze_concurrent_load.py
```

All analysis scripts work with data from **any scheduler** because the CSV format is standardized!

## Collecting Multiple Cluster Data

To build a multi-cluster comparison dataset:

1. Export from each cluster using appropriate script
2. Anonymize each separately (different mapping files!)
3. Add a "cluster" column to identify source
4. Combine for cross-cluster analysis

**Example:**
```bash
# Cluster A (SLURM)
./export_with_users.sh
./anonymize_cluster_data.sh slurm_jobs.csv clusterA_anon.csv mapA.txt
awk -F, 'NR==1{print $0",cluster"} NR>1{print $0",clusterA"}' clusterA_anon.csv > clusterA_labeled.csv

# Cluster B (UGE)
./export_uge_data.sh 01/01/2024 12/31/2024
./anonymize_cluster_data.sh uge_jobs.csv clusterB_anon.csv mapB.txt
awk -F, 'NR==1{print $0",cluster"} NR>1{print $0",clusterB"}' clusterB_anon.csv > clusterB_labeled.csv

# Combine
cat clusterA_labeled.csv > combined.csv
tail -n +2 clusterB_labeled.csv >> combined.csv

# Analyze
python3 analyze_submission_abandonment_events.py
```

## Testing Submission Abandonment Hypothesis

To test if users avoid submitting during congestion:

1. **Export data** from your scheduler
2. **Anonymize** the data
3. **Run analysis:**
   ```bash
   python3 analyze_submission_abandonment_events.py
   ```

**Expected results on different cluster types:**

| Cluster Type | Utilization | Queue Wait | Expected Correlation |
|--------------|-------------|------------|---------------------|
| **Overprovisioned** | <30% | <5 minutes | r ≈ -0.05 to -0.10 (weak) |
| **Well-sized** | 50-70% | 30 min - 2h | r ≈ -0.15 to -0.30 (moderate) |
| **Underprovisioned** | >80% | >2 hours | r ≈ -0.30 to -0.50 (strong) |

## Troubleshooting

### Script fails with "command not found"

**Problem:** Scheduler commands not in PATH

**Solution:**
```bash
# Find scheduler commands
which sacct    # SLURM
which qacct    # UGE
which bhist    # LSF
which condor_history  # HTCondor

# Add to PATH if needed
export PATH=$PATH:/opt/pbs/bin
export PATH=$PATH:/opt/lsf/bin
```

### No data exported

**Problem:** Date range doesn't match data

**Solution:** Check accounting logs and adjust dates
```bash
# SLURM: Check what dates have data
sacct --starttime 2020-01-01 | head -5

# UGE: Check accounting files
ls /opt/uge/default/common/accounting/

# PBS: Check accounting directory
ls /var/spool/pbs/server_priv/accounting/
```

### Permission denied

**Problem:** Need admin privileges

**Solution:**
```bash
# Run as scheduler admin or root
sudo ./export_<scheduler>_data.sh

# Or request admin to run export for you
```

### Export is very slow

**Problem:** Too much data or inefficient query

**Solution:**
- Limit date range to recent months
- Export in chunks (monthly)
- Use scheduler-specific optimizations (see notes above)

## Privacy & Security

**Best Practices:**

1. **Export on secure system**
   - Run export scripts only on scheduler head nodes
   - Never export to shared/public filesystems

2. **Anonymize immediately**
   - Run anonymization right after export
   - Delete raw export file after anonymization

3. **Secure mapping file**
   ```bash
   chmod 600 mapping_secure.txt
   chown root:root mapping_secure.txt
   mv mapping_secure.txt /root/secure/
   ```

4. **Encrypt for transfer**
   ```bash
   gpg -c jobs_anonymized.csv
   scp jobs_anonymized.csv.gpg analyst@remote:/secure/
   ```

5. **Access control**
   - Only cluster admins should run export scripts
   - Only authorized analysts should receive anonymized data
   - Maintain audit trail of who accessed data

## Support & Contributions

**Questions?**
- Check scheduler-specific notes above
- Review ANONYMIZATION_README.md for privacy details
- Review INSTITUTIONAL_APPROVAL_CASE.md for approval process

**Found a bug?**
- Most likely in date format parsing
- Check your scheduler version's output format
- Adjust Python parsing code in export script

**Adding a new scheduler?**
- Use existing scripts as template
- Maintain standard CSV column names
- Test with anonymization script
- Submit PR!

---

**Remember:** The goal is to collect comparable data from multiple schedulers to test the submission abandonment hypothesis across different cluster types and workloads. The standardized CSV format makes this possible!
