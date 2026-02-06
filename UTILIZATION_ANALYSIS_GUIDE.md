# True Utilization Analysis Guide

Complete guide for analyzing cluster utilization with comprehensive statistics and time series visualization.

## Overview

The true utilization analysis calculates cluster resource usage at every job transition point (start/end), providing:

- **Node-level metrics**: Busy/idle status
- **CPU-level metrics**: Allocated CPUs vs total capacity
- **Memory-level metrics**: Allocated memory vs total capacity
- **Comprehensive statistics**: Mean, median, percentiles, time-weighted averages
- **Time series output**: Ready for visualization and further analysis

## Quick Start

### Step 1: Analyze Utilization

```bash
# With cluster configuration (recommended)
python3 analyze_true_utilization.py jobs_anonymized.csv cluster_config.csv

# Without cluster configuration (absolute values only)
python3 analyze_true_utilization.py jobs_anonymized.csv
```

**Outputs:**
- `utilization_timeseries.csv` - Time series data
- `utilization_statistics.csv` - Summary statistics

### Step 2: Visualize (Optional)

```bash
python3 visualize_utilization.py utilization_timeseries.csv
```

**Outputs:**
- `cpu_utilization_timeline.png`
- `memory_utilization_timeline.png`
- `utilization_combined.png`
- `utilization_distributions.png`
- `utilization_daily.png`

---

## Detailed Usage

### analyze_true_utilization.py

**Purpose:** Calculate utilization at job transition times

**Syntax:**
```bash
python3 analyze_true_utilization.py <jobs_csv> [cluster_config_csv]
```

**Arguments:**
- `jobs_csv` - Anonymized job data (required)
- `cluster_config_csv` - Cluster configuration (optional but recommended)

**What it does:**
1. Loads job data and cluster configuration
2. Creates timeline of job start/end events
3. Calculates resource allocation at each event
4. Computes utilization percentages (if capacity known)
5. Generates comprehensive statistics
6. Outputs time series and summary data

**Output Files:**

#### utilization_timeseries.csv
```csv
timestamp_str,timestamp,event_type,cpus_allocated,cpu_utilization_pct,memory_allocated_mb,memory_utilization_pct
2024-01-01 00:05:23,2024-01-01T00:05:23,start,128,0.92,524288,1.2
2024-01-01 00:06:15,2024-01-01T00:06:15,end,96,0.69,393216,0.9
...
```

**Columns:**
- `timestamp_str` - Human-readable timestamp
- `timestamp` - ISO 8601 timestamp
- `event_type` - 'start' or 'end'
- `cpus_allocated` - Total CPUs in use
- `cpu_utilization_pct` - CPU utilization percentage
- `memory_allocated_mb` - Total memory in use (MB)
- `memory_utilization_pct` - Memory utilization percentage

#### utilization_statistics.csv
```csv
resource,metric,value,unit
CPU,mean,56.7,percent
CPU,median,52.3,percent
CPU,std,18.2,percent
CPU,p90,78.5,percent
CPU,p95,85.2,percent
...
```

**Statistics calculated:**
- `mean` - Average utilization
- `median` - Median utilization
- `std` - Standard deviation
- `min` / `max` - Range
- `p25`, `p75`, `p90`, `p95`, `p99` - Percentiles
- `time_weighted` - Time-weighted average (accounts for duration)

---

### visualize_utilization.py

**Purpose:** Create publication-quality charts

**Syntax:**
```bash
python3 visualize_utilization.py <timeseries_csv>
```

**Arguments:**
- `timeseries_csv` - Output from analyze_true_utilization.py

**Generated Charts:**

#### 1. cpu_utilization_timeline.png
Line chart of CPU utilization over time with:
- Mean and median lines
- Full time range
- Gridlines for readability

#### 2. memory_utilization_timeline.png
Line chart of memory utilization over time

#### 3. utilization_combined.png
Dual-panel chart showing CPU and memory on same timeline

#### 4. utilization_distributions.png
Histograms showing distribution of utilization values

#### 5. utilization_daily.png
Daily average utilization (smoothed view)

**Chart specifications:**
- Resolution: 300 DPI (publication quality)
- Format: PNG
- Size: 14" x 6" (timelines), 14" x 10" (combined)

---

## Understanding the Metrics

### CPU Utilization

**Definition:** Percentage of total cluster CPUs allocated to running jobs

**Formula:** `(CPUs allocated / Total cluster CPUs) × 100`

**Example:**
```
Cluster capacity: 13,920 CPUs
Jobs using: 7,883 CPUs
CPU utilization: 56.6%
```

**Interpretation:**
- **0-30%**: Underutilized (overprovisioned)
- **30-70%**: Well-utilized (good balance)
- **70-90%**: Highly utilized (may need expansion)
- **90-100%**: Fully utilized (users likely queuing)

### Memory Utilization

**Definition:** Percentage of total cluster memory allocated to running jobs

**Formula:** `(Memory allocated / Total cluster memory) × 100`

**Note:** Based on requested memory, not actual usage

**Interpretation:**
- Memory and CPU utilization may differ significantly
- Some jobs request more memory than they use
- High memory util + low CPU util = memory-bound workload

### Time-Weighted Average

**Definition:** Average utilization accounting for duration

**Why it matters:**
- Simple mean treats all time points equally
- Time-weighted mean accounts for how long each state lasted
- More accurate representation of true utilization

**Formula:**
```
Time-weighted avg = Σ(utilization × duration) / Σ(duration)
```

**Example:**
```
State 1: 50% util for 1 hour  → 50 × 3600 = 180,000
State 2: 80% util for 3 hours → 80 × 10800 = 864,000
Total time: 4 hours = 14,400 seconds

Time-weighted avg = (180,000 + 864,000) / 14,400 = 72.5%
Simple mean = (50 + 80) / 2 = 65%
```

---

## Complete Workflow Example

### Scenario: Analyze SLURM cluster utilization

```bash
# Step 1: Export data
./export_with_users.sh
./export_slurm_cluster_config.sh

# Step 2: Anonymize
./anonymize_cluster_data.sh \
  slurm_jobs_with_users.csv \
  jobs_anon.csv \
  mapping.txt

# Step 3: Analyze utilization
python3 analyze_true_utilization.py \
  jobs_anon.csv \
  slurm_cluster_config_20250206.csv

# Step 4: Visualize
python3 visualize_utilization.py \
  utilization_timeseries.csv

# Step 5: Review outputs
ls -lh *.csv *.png
```

**Output files:**
```
utilization_timeseries.csv           - Time series data
utilization_statistics.csv           - Summary stats
cpu_utilization_timeline.png         - CPU chart
memory_utilization_timeline.png      - Memory chart
utilization_combined.png             - Combined chart
utilization_distributions.png        - Histograms
utilization_daily.png                - Daily averages
```

---

## Use Cases

### 1. Capacity Planning

**Question:** Is our cluster appropriately sized?

**Metrics to check:**
- **Peak utilization** > 90% → Need expansion
- **Mean utilization** < 30% → Overprovisioned
- **P95 utilization** → Plan for 95th percentile demand

**Example analysis:**
```
CPU Stats:
  Mean:       56.6%  ← Average usage
  P95:        85.2%  ← Plan capacity for this
  Max:        97.8%  ← Occasional peaks

Conclusion: Well-sized. 95th percentile at 85% means cluster
handles most demand with headroom for growth.
```

### 2. Cloud Bursting ROI

**Question:** When should we burst to AWS?

**Approach:**
1. Find periods where utilization > capacity
2. Calculate overflow CPUs needed
3. Price AWS spot instances
4. Compare to expanding on-prem

**Using time series:**
```python
import pandas as pd

df = pd.read_csv('utilization_timeseries.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Find overflow periods (>100% utilization)
overflow = df[df['cpu_utilization_pct'] > 100]

# Calculate total overflow CPU-hours
df['time_delta'] = df['timestamp'].diff().dt.total_seconds() / 3600
overflow_cpu_hours = (overflow['cpus_allocated'] - capacity) * overflow['time_delta']

# Price AWS
aws_spot_price = 0.05  # per CPU-hour
cost = overflow_cpu_hours.sum() * aws_spot_price

print(f"Annual cloud bursting cost: ${cost * 365 / days_analyzed:,.0f}")
```

### 3. Workload Characterization

**Question:** What type of workload do we have?

**Check:**
- **Steady utilization** → Batch processing, simulations
- **Bursty utilization** → Interactive, deadline-driven
- **CPU high, memory low** → Compute-intensive
- **Memory high, CPU low** → Memory-intensive, data analysis

**Using distributions:**
```
Check utilization_distributions.png:
- Narrow peak → Consistent workload
- Wide distribution → Variable workload
- Bimodal → Two distinct usage patterns (day/night, etc.)
```

### 4. Resource Optimization

**Question:** Are users requesting appropriate resources?

**Compare:**
- Allocated CPUs vs. actual cluster capacity
- Allocated memory vs. actual cluster capacity
- If memory util << CPU util: Users over-requesting memory

**Action:**
- Educate users on right-sizing jobs
- Implement policies for resource requests
- Use time series to find specific users/times

---

## Advanced Analysis

### Export to R for Statistical Analysis

```r
# Load data
library(tidyverse)

ts <- read_csv('utilization_timeseries.csv')
ts$timestamp <- as.POSIXct(ts$timestamp)

# Time series decomposition
library(forecast)
cpu_ts <- ts(ts$cpu_utilization_pct, frequency=24*7)  # Weekly pattern
decomp <- stl(cpu_ts, s.window="periodic")
plot(decomp)

# Autocorrelation
acf(ts$cpu_utilization_pct)
```

### Export to Excel for Business Analysis

```bash
# time series already in CSV format
# Open utilization_timeseries.csv in Excel

# Create charts:
# 1. Insert → Chart → Line Chart
# 2. X-axis: timestamp_str
# 3. Y-axis: cpu_utilization_pct
# 4. Add trendline for capacity planning
```

### Custom Python Analysis

```python
import pandas as pd
import numpy as np

df = pd.read_csv('utilization_timeseries.csv', parse_dates=['timestamp'])

# Find peak usage hours
df['hour'] = df['timestamp'].dt.hour
hourly_avg = df.groupby('hour')['cpu_utilization_pct'].mean()
print("Peak hour:", hourly_avg.idxmax())

# Find day of week patterns
df['dayofweek'] = df['timestamp'].dt.dayofweek  # 0=Monday
daily_avg = df.groupby('dayofweek')['cpu_utilization_pct'].mean()
print("Busiest day:", ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][daily_avg.idxmax()])

# Identify sustained high utilization periods
high_util = df[df['cpu_utilization_pct'] > 80]
print(f"Time at >80% util: {len(high_util) / len(df) * 100:.1f}%")
```

---

## Troubleshooting

### "No cluster config provided" warning

**Issue:** Running without cluster configuration file

**Impact:**
- No utilization percentages calculated
- Only absolute allocations shown

**Solution:** Provide cluster config file:
```bash
python3 analyze_true_utilization.py jobs.csv cluster_config.csv
```

### Large memory usage during analysis

**Issue:** Time series with millions of jobs creates large DataFrames

**Solutions:**
1. **Analyze in chunks** (by date range)
2. **Subsample** time series for visualization
3. **Use more memory** (run on larger machine)

### Negative utilization values

**Issue:** Floating point errors or data issues

**Fix:** Script automatically clamps to 0

**If persistent:**
- Check job data for errors
- Verify start_time < end_time for all jobs
- Check for duplicate job IDs

### Visualizations don't show

**Issue:** matplotlib not installed

**Solution:**
```bash
pip install matplotlib pandas
```

---

## Performance Tips

### Large Datasets (>1M jobs)

**Optimize:**
```bash
# 1. Filter to date range first
python3 << EOF
import pandas as pd
df = pd.read_csv('jobs.csv', parse_dates=['start_time','end_time'])
df = df[(df['start_time'] >= '2024-01-01') & (df['end_time'] <= '2024-12-31')]
df.to_csv('jobs_filtered.csv', index=False)
EOF

# 2. Analyze filtered data
python3 analyze_true_utilization.py jobs_filtered.csv cluster_config.csv
```

### Faster Visualization

**For quick preview:**
```python
# Subsample time series
df = pd.read_csv('utilization_timeseries.csv')
df_sample = df.sample(n=10000)  # Random 10k points
df_sample.to_csv('ts_sample.csv', index=False)

# Visualize sample
python3 visualize_utilization.py ts_sample.csv
```

---

## Output File Reference

| File | Size | Purpose | Format |
|------|------|---------|--------|
| `utilization_timeseries.csv` | ~1MB per 100k events | Time series data | CSV |
| `utilization_statistics.csv` | <1KB | Summary stats | CSV |
| `cpu_utilization_timeline.png` | ~500KB | CPU chart | PNG 300DPI |
| `memory_utilization_timeline.png` | ~500KB | Memory chart | PNG 300DPI |
| `utilization_combined.png` | ~800KB | Combined chart | PNG 300DPI |
| `utilization_distributions.png` | ~600KB | Histograms | PNG 300DPI |
| `utilization_daily.png` | ~400KB | Daily averages | PNG 300DPI |

---

## Related Documentation

- **TWO_PART_EXPORT_GUIDE.md** - Why you need config + job data
- **COMPLETE_TOOLKIT_SUMMARY.md** - Full toolkit overview
- **[Scheduler]_EXPORT_GUIDE.md** - Scheduler-specific export instructions

---

**Ready to analyze cluster utilization?** Start with:
```bash
python3 analyze_true_utilization.py jobs_anonymized.csv cluster_config.csv
```
