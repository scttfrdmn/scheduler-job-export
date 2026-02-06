# Complete Cluster Analysis: Two-Part Export

To properly analyze a cluster, you need **TWO types of data**:

## Part 1: Job History (What Happened)
## Part 2: Cluster Configuration (What Exists)

Without both, you can't calculate true utilization!

---

## Why You Need Both

### The OSCAR Problem

With OSCAR, we had:
- ✅ Job history (6.9M jobs)
- ❌ Cluster configuration

**What we knew:**
- Peak concurrent usage: 14,645 CPUs
- Mean concurrent usage: 7,883 CPUs
- 435 unique nodes appeared in job data

**What we didn't know:**
- Total cluster size (could be 435 nodes or 1,000 nodes!)
- Actual CPUs per node (guessed 192, actually 32!)
- True utilization percentage (claimed 10%, might be 50%+!)

**The problem:** We only saw nodes that RAN jobs, not nodes that EXIST.

---

## Complete Export Process

### Step 1: Export Cluster Configuration

Shows what EXISTS (not what was used):

**SLURM:**
```bash
./export_slurm_cluster_config.sh
# OR use the auto-detect script:
./export_cluster_configs_all.sh
```

**Output:** `slurm_config.csv` with:
- ALL nodes (including idle ones)
- CPUs per node (actual hardware)
- Memory per node
- Node types (GPU, high-mem, etc.)
- Partitions
- Node states

**Other schedulers:**
The `export_cluster_configs_all.sh` script auto-detects:
- UGE/SGE: Uses `qhost`
- PBS: Uses `pbsnodes -a`
- LSF: Uses `bhosts -l`
- HTCondor: Uses `condor_status`

### Step 2: Export Job History

Shows what HAPPENED:

```bash
# SLURM
./export_with_users.sh

# UGE
./export_uge_data.sh 01/01/2024 12/31/2024

# PBS
./export_pbs_data.sh 20240101 20241231

# LSF
./export_lsf_data.sh 2024/01/01 2024/12/31

# HTCondor
./export_htcondor_data.sh 365
```

**Output:** Job records with user, resources, timing

### Step 3: Anonymize Job Data

```bash
./anonymize_cluster_data.sh \
  jobs_with_users.csv \
  jobs_anonymized.csv \
  mapping_secure.txt
```

**Note:** Cluster config doesn't need anonymization (no user data)

### Step 4: Analyze Configuration

```bash
python3 analyze_cluster_config.py slurm_config.csv
```

**Shows:**
- Total cluster size
- CPUs per node distribution
- GPU vs compute nodes
- Partitions
- Node states (idle, down, allocated, etc.)

### Step 5: Calculate True Utilization

```bash
python3 analyze_concurrent_load.py
```

Then compare:

```
Cluster capacity: 13,920 CPUs (from config)
Peak usage:       14,645 CPUs (from jobs)
Mean usage:        7,883 CPUs (from jobs)

Peak utilization: 105% (!!! oversubscribed or wrong config!)
Mean utilization:  57% (actual utilization)
```

---

## What Each Export Shows

### Cluster Configuration Export

| Field | Description | Why It Matters |
|-------|-------------|----------------|
| Total nodes | ALL nodes in cluster | Can't calculate utilization without this |
| CPUs/node | Actual hardware specs | Guessing from jobs is unreliable |
| Memory/node | RAM available | Needed for capacity planning |
| Node types | GPU, high-mem, compute | Different utilization by type |
| Node states | idle, allocated, down | How much capacity is actually available |

### Job History Export

| Field | Description | Why It Matters |
|-------|-------------|----------------|
| User/Group | Who submitted | Behavioral analysis, power users |
| Resources | CPUs, memory requested | Usage patterns |
| Timing | Submit, start, end | Queue times, utilization over time |
| Nodes used | Which nodes ran jobs | But NOT all nodes! |

---

## Common Mistakes

### ❌ Mistake 1: Using Job Data to Infer Cluster Size

```python
# WRONG: Only shows nodes that ran jobs
unique_nodes = df['nodelist'].unique()
cluster_size = len(unique_nodes)  # Could be way off!
```

**Problem:**
- Idle nodes never appear in job data
- Down nodes never appear
- Reserved nodes might not appear
- Underestimates true cluster size

**Solution:** Export actual cluster config with `sinfo` / `qhost` / `pbsnodes`

### ❌ Mistake 2: Inferring CPUs per Node from Jobs

```python
# WRONG: Unreliable inference
cpus_per_node = df.groupby('nodelist')['cpus_req'].max()
```

**Problem:**
- Jobs might not request all CPUs
- Hyperthreading makes this confusing
- Jobs might request logical CPUs, config shows physical cores

**Solution:** Get actual hardware specs from cluster config

### ❌ Mistake 3: Calculating Utilization Without Cluster Size

```python
# WRONG: No denominator!
mean_usage = 7,883 CPUs
utilization = ???  # Don't know total capacity!
```

**Solution:** Export cluster config first

---

## Real-World Example: OSCAR

### What We Had (Job Data Only)

```
Jobs analyzed: 6,991,376
Peak concurrent: 14,645 CPUs
Mean concurrent: 7,883 CPUs
Unique nodes seen: 435
Inferred CPUs/node: 192 (WRONG!)
Calculated capacity: 76,800 CPUs (WRONG!)
Calculated utilization: 10.26% (WRONG!)
```

### What We Should Have Done

**Step 1: Export cluster config**
```bash
sinfo -N -o "%N,%c,%m,%G,%P,%T"
```

**Would have shown:**
```
Total nodes: 435
CPUs per node: 32 (not 192!)
Total capacity: 13,920 CPUs (not 76,800!)
```

**Step 2: Calculate TRUE utilization**
```
Mean usage: 7,883 CPUs
True capacity: 13,920 CPUs
TRUE utilization: 56.6% (not 10.26%!)
```

**Completely different conclusion:**
- ❌ "Overprovisioned throughput cluster at 10% utilization"
- ✅ "Well-utilized cluster at 57% average utilization"

---

## For Data Collection Campaign

When collecting data from multiple sites, request **BOTH**:

### 1. Cluster Configuration

```bash
# Auto-detect and export
./export_cluster_configs_all.sh
```

**Deliverable:** `<site>_config.csv`

### 2. Job History

```bash
# Choose appropriate scheduler script
./export_<scheduler>_data.sh [dates]
./anonymize_cluster_data.sh jobs.csv jobs_anon.csv mapping.txt
```

**Deliverable:** `<site>_jobs_anonymized.csv`

### 3. Combined Analysis

```python
# Load both
config = pd.read_csv('site_config.csv')
jobs = pd.read_csv('site_jobs_anonymized.csv')

# Calculate metrics
total_capacity = config['CPUs'].sum()
peak_usage = calculate_peak_concurrent(jobs)
mean_usage = calculate_mean_concurrent(jobs)

# True utilization
peak_util = peak_usage / total_capacity
mean_util = mean_usage / total_capacity

print(f"Site: {site}")
print(f"Capacity: {total_capacity:,} CPUs")
print(f"Peak utilization: {peak_util:.1%}")
print(f"Mean utilization: {mean_util:.1%}")
```

---

## Updated Data Collection Checklist

For each cluster site:

- [ ] **Part 1: Cluster Configuration**
  - [ ] Run `export_cluster_configs_all.sh` (auto-detects scheduler)
  - [ ] Verify all nodes appear in output
  - [ ] Check CPUs per node looks correct
  - [ ] Note any special node types (GPU, high-mem)

- [ ] **Part 2: Job History**
  - [ ] Run appropriate `export_<scheduler>_data.sh`
  - [ ] Specify date range (recommend 1 year)
  - [ ] Verify user/group columns exist
  - [ ] Run anonymization script

- [ ] **Part 3: Metadata**
  - [ ] Record cluster name/site
  - [ ] Record scheduler type and version
  - [ ] Record any special configuration notes
  - [ ] Document known issues (downtime, upgrades, etc.)

- [ ] **Part 4: Delivery**
  - [ ] `<site>_config.csv` (cluster configuration)
  - [ ] `<site>_jobs_anonymized.csv` (anonymized job history)
  - [ ] `<site>_metadata.txt` (notes about cluster)
  - [ ] Keep `mapping_secure.txt` PRIVATE at site

---

## Summary

**Before (Job Data Only):**
- ❌ Can't know true cluster size
- ❌ Can't calculate actual utilization
- ❌ Might guess wrong by 5-10x
- ❌ Wrong conclusions about overprovisioning

**After (Config + Job Data):**
- ✅ Know exact cluster capacity
- ✅ Calculate true utilization
- ✅ Accurate peak vs mean analysis
- ✅ Correct assessment of provisioning

**Bottom line:** Always export cluster configuration alongside job history!

---

## Scripts Summary

| Purpose | Script | What It Does |
|---------|--------|--------------|
| **Config export (auto)** | `export_cluster_configs_all.sh` | Auto-detects scheduler, exports config |
| **Config export (SLURM)** | `export_slurm_cluster_config.sh` | SLURM-specific config export |
| **Job export (SLURM)** | `export_with_users.sh` | SLURM job history |
| **Job export (UGE)** | `export_uge_data.sh` | UGE/SGE job history |
| **Job export (PBS)** | `export_pbs_data.sh` | PBS/Torque job history |
| **Job export (LSF)** | `export_lsf_data.sh` | LSF job history |
| **Job export (HTCondor)** | `export_htcondor_data.sh` | HTCondor job history |
| **Anonymize** | `anonymize_cluster_data.sh` | Anonymize job data (any scheduler) |
| **Analyze config** | `analyze_cluster_config.py` | Calculate cluster size/composition |
| **Analyze jobs** | `analyze_concurrent_load.py` | Calculate utilization from jobs |

All scripts are scheduler-aware and produce compatible output formats!
