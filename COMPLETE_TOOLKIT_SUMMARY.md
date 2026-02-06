# Complete Multi-Scheduler Data Collection Toolkit

**Status: Production Ready** ✅

This toolkit provides comprehensive data export and analysis for **all major HPC schedulers**. All scripts output standardized CSV format compatible with the anonymization and analysis tools.

---

## 📋 Complete Script Inventory

### Job History Export (Part 1)

| Scheduler | Script | Format | Status |
|-----------|--------|--------|--------|
| **SLURM** | `export_with_users.sh` | Native CSV | ✅ Production |
| **LSF** | `export_lsf_comprehensive.sh` | Text → CSV | ✅ Production |
| **PBS/Torque** | `export_pbs_comprehensive.sh` | Logs → CSV | ✅ Production |
| **UGE/SGE** | `export_uge_comprehensive.sh` | Text → CSV | ✅ Production |
| **HTCondor** | `export_htcondor_data.sh` | TSV → CSV | ✅ Production |

**Output:** All produce identical CSV with columns:
```
user,group,account,job_id,job_name,queue,cpus,mem_req,nodes,
nodelist,submit_time,start_time,end_time,exit_status
```

### Cluster Configuration Export (Part 2)

| Scheduler | Script | Command Used | Status |
|-----------|--------|--------------|--------|
| **SLURM** | `export_slurm_cluster_config.sh` | `sinfo` | ✅ Production |
| **LSF** | `export_lsf_cluster_config.sh` | `bhosts`, `lshosts` | ✅ Production |
| **PBS/Torque** | `export_pbs_cluster_config.sh` | `pbsnodes` | ✅ Production |
| **UGE/SGE** | `export_uge_cluster_config.sh` | `qhost` | ✅ Production |
| **All** | `export_cluster_configs_all.sh` | Auto-detects | ✅ Production |

**Output:** Scheduler-specific formats (standardize with `standardize_cluster_config.py`)

### Anonymization & Utilities

| Script | Purpose | Status |
|--------|---------|--------|
| `anonymize_cluster_data.sh` | Anonymize user/group data | ✅ Production |
| `standardize_cluster_config.py` | Normalize config formats | ✅ Production |
| `analyze_cluster_config.py` | Analyze cluster capacity | ✅ Production |
| `analyze_concurrent_load.py` | Calculate utilization | ✅ Production |
| `analyze_submission_abandonment_events.py` | Test hypothesis | ✅ Production |

---

## 🚀 Quick Start by Scheduler

### SLURM

```bash
# Cluster config
./export_slurm_cluster_config.sh

# Job history
./export_with_users.sh

# Anonymize
./anonymize_cluster_data.sh \
  slurm_jobs_with_users.csv \
  slurm_anonymized.csv \
  slurm_mapping.txt

# Analyze
python3 analyze_concurrent_load.py
python3 analyze_submission_abandonment_events.py
```

### LSF (IBM Spectrum LSF)

```bash
# Source LSF environment
source /opt/lsf/conf/profile.lsf

# Cluster config
./export_lsf_cluster_config.sh

# Job history
./export_lsf_comprehensive.sh 2024/01/01 2024/12/31

# Anonymize
./anonymize_cluster_data.sh \
  lsf_jobs_with_users_20250129.csv \
  lsf_anonymized.csv \
  lsf_mapping.txt

# Analyze
python3 analyze_concurrent_load.py
python3 analyze_submission_abandonment_events.py
```

### PBS/Torque/PBS Pro

```bash
# Set PBS environment if needed
export PBS_HOME=/opt/pbs

# Cluster config
./export_pbs_cluster_config.sh

# Job history (may need sudo for accounting logs)
sudo ./export_pbs_comprehensive.sh 20240101 20241231

# Anonymize
./anonymize_cluster_data.sh \
  pbs_jobs_with_users_20250129.csv \
  pbs_anonymized.csv \
  pbs_mapping.txt

# Analyze
python3 analyze_concurrent_load.py
python3 analyze_submission_abandonment_events.py
```

### UGE/SGE/OGE

```bash
# Source Grid Engine environment
source $SGE_ROOT/default/common/settings.sh

# Cluster config
./export_uge_cluster_config.sh

# Job history
./export_uge_comprehensive.sh 01/01/2024 12/31/2024

# Anonymize
./anonymize_cluster_data.sh \
  uge_jobs_with_users_20250129.csv \
  uge_anonymized.csv \
  uge_mapping.txt

# Analyze
python3 analyze_concurrent_load.py
python3 analyze_submission_abandonment_events.py
```

---

## 📊 Standard Workflow

### Phase 1: Export Data

```bash
# Step 1: Cluster Configuration (what exists)
./export_<scheduler>_cluster_config.sh

# Step 2: Job History (what happened)
./export_<scheduler>_comprehensive.sh [date_range]

# Output:
#   - <scheduler>_cluster_config_YYYYMMDD.csv
#   - <scheduler>_jobs_with_users_YYYYMMDD.csv
```

### Phase 2: Anonymize

```bash
# Anonymize job data (config doesn't need anonymization)
./anonymize_cluster_data.sh \
  <scheduler>_jobs_with_users_YYYYMMDD.csv \
  <scheduler>_jobs_anonymized.csv \
  <scheduler>_mapping_secure.txt

# Secure the mapping file
chmod 600 <scheduler>_mapping_secure.txt
sudo mv <scheduler>_mapping_secure.txt /root/secure/

# Delete original with real usernames
rm <scheduler>_jobs_with_users_YYYYMMDD.csv
```

### Phase 3: Standardize (Optional)

```bash
# Standardize cluster config for cross-scheduler comparison
python3 standardize_cluster_config.py \
  <scheduler>_cluster_config_YYYYMMDD.csv

# Creates: <scheduler>_cluster_config_YYYYMMDD_standardized.csv
```

### Phase 4: Analyze

```bash
# 1. Cluster capacity
python3 analyze_cluster_config.py \
  <scheduler>_cluster_config_YYYYMMDD_standardized.csv

# 2. Job utilization
python3 analyze_concurrent_load.py

# 3. Submission abandonment (test hypothesis!)
python3 analyze_submission_abandonment_events.py
```

---

## 🔑 Key Features

### 1. Standardized Output

**All job exports produce identical CSV:**
- ✅ Same column names across all schedulers
- ✅ Same date format (ISO 8601)
- ✅ Same resource units (CPUs, MB)
- ✅ Works with one anonymization script
- ✅ Works with all analysis scripts

### 2. Comprehensive Data Collection

**Job History includes:**
- User and group information (for behavioral analysis)
- Resource requests (CPUs, memory, nodes)
- Timing data (submit, start, end)
- Queue/partition information
- Exit status

**Cluster Config includes:**
- All nodes/hosts (not just those that ran jobs)
- Hardware specs (CPUs, memory per node)
- Node types (compute, GPU, high-memory)
- Node states (idle, allocated, down)
- Actual cluster capacity

### 3. Privacy & Security

**Anonymization:**
- Deterministic mapping (same user always → same anonymous ID)
- Preserves patterns (user behavior, group patterns)
- Auto-detects user/group columns
- Creates secure mapping file
- Anonymizes users, groups, accounts
- Keeps everything else intact

**Security:**
- Scripts check for admin privileges where needed
- Mapping files have instructions for secure storage
- Can delete original data after anonymization
- No data leaves the site unencrypted

### 4. Error Handling

**All scripts include:**
- Environment checks (is scheduler installed?)
- Permission fallbacks (try admin, fall back to user-only)
- Date format validation
- File access verification
- Clear error messages
- Troubleshooting guidance

---

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| `MULTI_SCHEDULER_EXPORT_README.md` | Overview of all schedulers |
| `TWO_PART_EXPORT_GUIDE.md` | Why you need config + jobs |
| `LSF_EXPORT_GUIDE.md` | LSF-specific details |
| `ANONYMIZATION_README.md` | Privacy and anonymization |
| `INSTITUTIONAL_APPROVAL_CASE.md` | How to get approval |
| `COMPLETE_TOOLKIT_SUMMARY.md` | This file |

---

## 🎯 Data Collection Campaign

### Goal
Collect data from 10-20 HPC sites with different characteristics to test the submission abandonment hypothesis.

### Target Sites

**By Scheduler:**
- 3-5 SLURM sites (universities, national labs)
- 2-3 LSF sites (national labs, commercial)
- 2-3 PBS sites (DOD, research institutions)
- 1-2 UGE sites (older installations)
- 1-2 HTCondor sites (HTC workloads)

**By Utilization:**
- 3-5 overprovisioned (like OSCAR) - expect weak signal
- 5-10 normally loaded - expect moderate signal
- 2-5 heavily contended (4-7x underprovisioned) - expect strong signal

**By Scale:**
- 3-5 small clusters (100-500 nodes)
- 5-10 medium clusters (500-5000 nodes)
- 2-5 large clusters (5000+ nodes)

### Data Requirements per Site

**Minimum:**
- ✅ Cluster configuration export (one snapshot)
- ✅ Job history export (6-12 months)
- ✅ Anonymized data only
- ✅ Basic metadata (scheduler type, rough scale)

**Ideal:**
- ✅ Multiple snapshots of cluster config (if it changed)
- ✅ 1-2 years of job history
- ✅ Information about workload type (HPC, HTC, mixed)
- ✅ Known provisioning level if available

---

## 🔬 Expected Results

### By Cluster Type

| Cluster Type | Characteristics | Expected Correlation | Confidence |
|--------------|-----------------|---------------------|------------|
| **Overprovisioned** | <30% util, <5min wait | r = -0.05 to -0.15 | We found -0.09 on OSCAR |
| **Well-provisioned** | 50-70% util, <1h wait | r = -0.15 to -0.30 | Predicted |
| **Underprovisioned** | >80% util, >2h wait | r = -0.30 to -0.50 | Predicted |
| **Severely contended** | 4-7x under, >12h wait | r = -0.40 to -0.60 | Predicted |

### Statistical Power

With 10-20 sites:
- Can test effect across utilization levels
- Can control for scheduler type
- Can control for workload type (HPC vs HTC)
- Can detect even weak effects (power > 0.8)
- Can publish robust multi-site findings

---

## 🛠️ Troubleshooting

### Common Issues

**"Command not found"**
- Scheduler environment not sourced
- Solution: Source appropriate profile/settings file

**"Permission denied" on accounting data**
- Need admin/root privileges
- Solution: Run with sudo or request admin to export

**"No accounting files found"**
- Wrong date format for that scheduler
- Solution: Check scheduler-specific date format

**Empty or missing data**
- Date range too recent or too old
- Solution: Check available accounting data range

**Python errors during parsing**
- Scheduler output format differs from expected
- Solution: Check scheduler version, may need script adjustment

### Scheduler-Specific Issues

**SLURM:**
- `sacct` requires accounting database
- May need partition-specific export
- Check `sacct --starttime 2020-01-01` to verify data exists

**LSF:**
- `bhist -a` requires LSF admin
- Can fall back to `bhist` (your jobs only)
- `bacct` provides more details but slower

**PBS:**
- Accounting logs require root/PBS admin access
- Log files may be compressed (.gz, .bz2)
- Different PBS variants have slightly different formats

**UGE/SGE:**
- Date format is MM/DD/YYYY (unusual!)
- XML output more reliable than text
- `qacct` can be slow for large date ranges

---

## 📦 Deliverables per Site

### What to Collect

```
site_name/
  ├── site_cluster_config.csv              # Cluster inventory
  ├── site_jobs_anonymized.csv             # Anonymized job history
  ├── site_metadata.txt                    # Site information
  └── site_mapping_secure.txt              # KEEP PRIVATE AT SITE
```

### Site Metadata Template

```
Site Name: [Name or ID]
Scheduler: [SLURM/LSF/PBS/UGE/HTCondor]
Scheduler Version: [Version]
Collection Date: [YYYY-MM-DD]
Job History Period: [Start date] to [End date]
Total Nodes: [Number]
Total CPUs: [Number]
Workload Type: [HPC/HTC/Mixed]
Primary Discipline: [Physics/Biology/Chemistry/CS/Engineering/Mixed]
Known Utilization: [If available]
Notes: [Any relevant info]
```

---

## 🎓 Academic Use

### For Publication

This toolkit enables:
- Multi-site behavioral analysis
- Cross-scheduler comparison
- Utilization vs behavior correlation
- Resource provisioning recommendations
- Cloud bursting business case

### Citation

If you use this toolkit in research:
```
[Your paper citation here]

Data collected using multi-scheduler HPC job export toolkit
developed for submission abandonment behavioral analysis.
```

---

## 🔐 Security & Privacy

### Data Classification

**Private (Never Share):**
- ❌ Raw job exports with real usernames
- ❌ Mapping files (link anonymous ↔ real identities)
- ❌ Institutional identifiable information

**Shareable (After Anonymization):**
- ✅ Anonymized job history
- ✅ Cluster configuration (no user data)
- ✅ Aggregate statistics
- ✅ De-identified metadata

### Compliance Checklist

- [ ] Institutional approval obtained
- [ ] Data export authorized by admin
- [ ] Anonymization performed correctly
- [ ] Mapping file secured at site
- [ ] Original data deleted after anonymization
- [ ] Only anonymized data transmitted
- [ ] Data encrypted during transfer
- [ ] Data use agreement signed (if required)

---

## 🚀 Ready to Deploy

### For Site Admins

1. Choose your scheduler's scripts
2. Test on small date range first
3. Verify output looks correct
4. Run full export
5. Anonymize data
6. Secure mapping file
7. Verify anonymized data
8. Share anonymized CSV + metadata

### For Researchers

1. Receive anonymized CSV + metadata
2. Verify data integrity
3. Run analysis scripts
4. Compare across sites
5. Test hypothesis
6. Publish findings!

---

## 📊 Success Metrics

**Toolkit Quality:**
- ✅ Works on all major schedulers
- ✅ Standardized output format
- ✅ Complete anonymization
- ✅ Comprehensive documentation
- ✅ Production-ready error handling

**Data Collection:**
- 🎯 Target: 10-20 sites
- 🎯 Mixed scheduler types
- 🎯 Mixed utilization levels
- 🎯 Mixed scales
- 🎯 6-12 months of data per site

**Analysis:**
- 🎯 Test submission abandonment hypothesis
- 🎯 Quantify effect by utilization level
- 🎯 Compare schedulers
- 🎯 Business case for cloud bursting
- 🎯 Publication in HPC venue

---

**Status:** All components complete and production-ready! 🎉

Ready to collect data and test your hypothesis across the HPC ecosystem!
