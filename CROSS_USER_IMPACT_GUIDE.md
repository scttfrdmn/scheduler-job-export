# Cross-User Impact and Enhanced Submission Abandonment Analysis Guide

Complete guide for analyzing how individual user behaviors impact others and trigger submission abandonment.

## Overview

This enhanced analysis goes beyond simple correlation to identify **causal relationships** between user behaviors and system-wide impacts.

### What This Answers

**Primary Questions:**
- "Does User X's heavy-tailed job every Tuesday cause others to stop submitting?"
- "When User Y submits a 1000-core job, what happens to everyone else?"
- "How do large jobs from Group A impact submission rates in Group B?"
- "What specific events trigger submission abandonment?"

**Output Types:**
- ✅ **General patterns**: "User X impacts system every Tuesday at 8pm"
- ✅ **Specific incidents**: "On 2024-03-15 at 14:23, User X started job causing 40% submission drop"
- ✅ **Temporal patterns**: "Tuesday evenings show highest abandonment trigger rate"
- ✅ **Cross-group dynamics**: "Group A's monthly batch impacts Group B most severely"

---

## Quick Start

### Step 1: Export and Anonymize Data

```bash
# Export cluster data
./export_slurm_cluster_config.sh
./export_with_users.sh

# Anonymize
./anonymize_cluster_data.sh \
  slurm_jobs_with_users.csv \
  jobs_anon.csv \
  mapping.txt
```

### Step 2: Run Cross-User Impact Analysis

```bash
python3 analyze_cross_user_impacts.py jobs_anon.csv slurm_cluster_config.csv
```

**Processing Time:** ~5-10 minutes for 1M jobs (samples top 1000 impact events)

### Step 3: Review Results

**Outputs:**
```
high_impact_jobs.csv                  - Jobs with significant system impact
impact_events.csv                     - Specific before/after comparisons
user_impact_patterns.csv              - Recurring patterns per user
submission_abandonment_triggers.csv   - Events causing abandonment
temporal_impact_patterns.csv          - When impacts occur
cross_group_impacts.csv               - Group-to-group relationships
```

---

## Understanding the Methodology

### 1. Identifying High-Impact Jobs

**Criteria for "high-impact":**
- Large CPU allocation (>10% of cluster or >90th percentile)
- Long runtime (>95th percentile)
- High CPU-hours consumed (>90th percentile)

**Impact Score (0-100):**
```
Impact Score = 0.3 × CPU_size + 0.3 × Runtime + 0.4 × CPU_hours
```

**Example:**
```
Job with 500 CPUs, 12 hour runtime, 6000 CPU-hours
→ Impact Score: 85.3
```

### 2. Measuring Before/After Effects

For each high-impact job, the analysis compares:

**Time Windows:**
- Before: 1 hour before job starts
- After: 2 hours after job starts

**Metrics Measured:**

#### Submission Rate
```
Rate = jobs_submitted / time_window_hours
Change% = (after - before) / before × 100
```

**Abandonment signal:** Drop >25%

#### Wait Time
```
Median wait time (minutes) before vs after
Change% = (after - before) / before × 100
```

**Congestion signal:** Increase >50%

#### Active Users
```
Unique users submitting in each window
Change% = (after - before) / before × 100
```

**Abandonment signal:** Drop >20%

### 3. Detecting Submission Abandonment

**Abandonment Trigger Criteria:**
- Submission rate drops >25%, **OR**
- Active user count drops >20%

**Why these thresholds?**
- 25% submission drop: Substantial, beyond normal variance
- 20% user drop: Multiple users affected, not just one

### 4. Pattern Identification

**Recurring patterns require:**
- Minimum 3 impact events from same user
- Temporal clustering (e.g., >50% on same day of week)
- Regular frequency (>0.5 events per week)

**Example Pattern:**
```
User: user_0042
Day: Tuesday (65% of events)
Time: 20:30 ± 2.1 hours
Frequency: 2.3 events/week
Impact: -38% submission rate, +85% wait time
Classification: Regular pattern, High abandonment trigger
```

---

## Interpreting Results

### high_impact_jobs.csv

**Columns:**
```csv
job_id, user, group, submit_time, start_time, end_time,
cpus, runtime_seconds, cpu_hours, impact_score,
day_of_week, hour_of_day, date
```

**Key Metrics:**
- `impact_score`: 0-100, higher = more significant
- `cpu_hours`: Total compute consumed
- `day_of_week`, `hour_of_day`: Temporal patterns

**Analysis Tips:**
```python
import pandas as pd

df = pd.read_csv('high_impact_jobs.csv')

# Find most impactful users
top_users = df.groupby('user')['impact_score'].agg(['count', 'mean']).sort_values('mean', ascending=False)

# Find temporal clustering
df['day_of_week'].value_counts()  # Which days?
df['hour_of_day'].hist()          # Which hours?

# Find largest jobs
df.nlargest(10, 'cpus')[['user', 'cpus', 'runtime_seconds', 'day_of_week']]
```

### impact_events.csv

**Critical Columns:**
```csv
impact_user, impact_time, impact_cpus, impact_score,
submit_rate_before, submit_rate_after, submit_rate_change_pct,
wait_time_before_min, wait_time_after_min, wait_time_change_pct,
active_users_before, active_users_after, users_change_pct,
is_abandonment_trigger, day_of_week, hour_of_day
```

**Example Analysis:**

#### Find Worst Incidents
```python
df = pd.read_csv('impact_events.csv')

# Most severe submission drops
worst = df.nsmallest(10, 'submit_rate_change_pct')
print(worst[['impact_user', 'impact_time', 'submit_rate_change_pct', 'wait_time_change_pct']])
```

**Example Output:**
```
impact_user  impact_time          submit_rate_change_pct  wait_time_change_pct
user_0042    2024-03-15 20:23:15  -62.3                   +145.2
user_0137    2024-04-02 08:15:42  -58.1                   +98.7
user_0042    2024-03-22 20:18:33  -55.4                   +132.1
```

**Interpretation:** User_0042 is a recurring problem on Friday evenings!

#### Analyze Abandonment Triggers Only
```python
triggers = df[df['is_abandonment_trigger'] == True]

print(f"Total abandonment triggers: {len(triggers)}")
print(f"Percent of all events: {len(triggers)/len(df)*100:.1f}%")

# Who causes most triggers?
trigger_users = triggers.groupby('impact_user').size().sort_values(ascending=False)
print(trigger_users.head(10))
```

### user_impact_patterns.csv

**Columns:**
```csv
user, group, event_count, frequency_per_week,
most_common_day, day_concentration_pct,
avg_hour_of_day, hour_std,
avg_impact_score, avg_cpus,
avg_submit_rate_change_pct, avg_wait_time_change_pct,
abandonment_trigger_rate_pct, is_regular_pattern
```

**Key Insights:**

#### Identify Problematic Users
```python
df = pd.read_csv('user_impact_patterns.csv')

# Users with highest abandonment trigger rate
problems = df.nlargest(20, 'abandonment_trigger_rate_pct')

print("Most problematic users:")
print(problems[['user', 'event_count', 'abandonment_trigger_rate_pct',
                'most_common_day', 'avg_cpus']])
```

**Example Output:**
```
user       event_count  abandonment_trigger_rate_pct  most_common_day  avg_cpus
user_0042  47           74.5                          Tuesday          1245
user_0137  31           68.8                          Monday           892
user_0089  18           61.1                          Friday           2103
```

**Actionable Insight:**
- Contact user_0042 about Tuesday submissions
- Suggest off-peak times or job splitting
- Consider dedicated queue for large jobs

#### Find Regular Patterns
```python
regular = df[df['is_regular_pattern'] == True]

print(f"Users with regular impact patterns: {len(regular)}")

for _, row in regular.head(10).iterrows():
    print(f"\n{row['user']}:")
    print(f"  Submits: {row['frequency_per_week']:.1f}x per week")
    print(f"  Preferred day: {row['most_common_day']} ({row['day_concentration_pct']:.0f}%)")
    print(f"  Avg time: {row['avg_hour_of_day']:.1f}:00")
    print(f"  Impact: {row['avg_submit_rate_change_pct']:.1f}% submission change")
    print(f"  Triggers abandonment: {row['abandonment_trigger_rate_pct']:.0f}% of time")
```

### submission_abandonment_triggers.csv

**Analysis:**
```python
df = pd.read_csv('submission_abandonment_triggers.csv')

# Severity distribution
print(df['severity'].value_counts())

# Time of day analysis
print(df['time_of_day'].value_counts())

# User breakdown
print(df.groupby('impact_user').size().sort_values(ascending=False).head(10))

# Find extreme cases
extreme = df[df['severity'] == 'severe']
print(f"\nSevere abandonment events: {len(extreme)}")
print(extreme[['impact_user', 'impact_time', 'submit_rate_change_pct',
               'day_of_week', 'time_of_day']].head())
```

### temporal_impact_patterns.csv

**Columns:**
```csv
temporal_type, temporal_value, event_count,
abandonment_trigger_count, abandonment_rate_pct,
avg_submit_rate_change_pct, avg_wait_time_change_pct,
avg_impact_cpus
```

**Analysis:**
```python
df = pd.read_csv('temporal_impact_patterns.csv')

# By day of week
dow = df[df['temporal_type'] == 'day_of_week'].sort_values('abandonment_rate_pct', ascending=False)
print("Day of Week Impact:")
print(dow[['temporal_value', 'event_count', 'abandonment_rate_pct',
           'avg_submit_rate_change_pct']])

# By time of day
tod = df[df['temporal_type'] == 'hour_block'].sort_values('abandonment_rate_pct', ascending=False)
print("\nTime of Day Impact:")
print(tod[['temporal_value', 'event_count', 'abandonment_rate_pct']])
```

**Example Insights:**
```
Day of Week Impact:
Tuesday    125 events  38.4% abandonment rate  -32.1% submission change
Monday     118 events  35.6% abandonment rate  -28.7% submission change

Time of Day Impact:
20-24      89 events   42.7% abandonment rate
16-20      76 events   38.2% abandonment rate
```

**Interpretation:** Evening submissions (especially Tuesday/Monday nights) cause most disruption.

### cross_group_impacts.csv

**Columns:**
```csv
impact_group, affected_group, impact_event_count,
abandonment_trigger_count,
avg_submit_rate_change_pct, avg_wait_time_change_pct,
avg_impact_cpus, impact_strength
```

**Analysis:**
```python
df = pd.read_csv('cross_group_impacts.csv')

# Strongest impacts
top = df.nlargest(10, 'impact_strength')

print("Strongest Cross-Group Impacts:")
for _, row in top.iterrows():
    print(f"\n{row['impact_group']} → {row['affected_group']}:")
    print(f"  Events: {row['impact_event_count']}")
    print(f"  Abandonment triggers: {row['abandonment_trigger_count']}")
    print(f"  Submission change: {row['avg_submit_rate_change_pct']:.1f}%")
    print(f"  Wait time change: {row['avg_wait_time_change_pct']:.1f}%")
```

---

## Use Cases

### 1. Identify Submission Abandonment Root Causes

**Question:** What causes users to stop submitting?

**Approach:**
1. Review `submission_abandonment_triggers.csv` for all trigger events
2. Group by `impact_user` to find repeat offenders
3. Check `user_impact_patterns.csv` for their regular patterns
4. Use `impact_events.csv` for specific incident details

**Example Finding:**
```
Root cause: user_0042's Tuesday evening batch jobs (1200+ CPUs)
Effect: 38% drop in submission rate, 85% increase in wait times
Frequency: 2-3 times per week
Recommendation: Move to dedicated queue or off-peak hours
```

### 2. Understand Group Dynamics

**Question:** How do research groups affect each other?

**Approach:**
1. Analyze `cross_group_impacts.csv` for group relationships
2. Find strongest impact pairs
3. Check `temporal_impact_patterns.csv` for when it happens
4. Review `user_impact_patterns.csv` to identify key users in each group

**Example Finding:**
```
Group_A (bioinformatics) → Group_B (chemistry)
- 47 impact events per month
- 32% abandonment trigger rate
- Strongest on Monday mornings
- Primary culprit: user_0137 (Group_A) with long BLAST jobs
```

### 3. Capacity Planning Based on Impact

**Question:** If we can't expand capacity, how do we reduce impacts?

**Approach:**
1. Identify high-impact users from `user_impact_patterns.csv`
2. Analyze their `most_common_day` and `avg_hour_of_day`
3. Check `temporal_impact_patterns.csv` for overall busy periods
4. Design policies around these patterns

**Example Policy:**
```
Policy: Large Job Scheduling Windows

Based on analysis:
- Tuesday 20:00-24:00 shows 42.7% abandonment rate
- Monday 16:00-20:00 shows 38.2% abandonment rate
- user_0042, user_0137, user_0089 cause 68% of severe events

New Policy:
- Jobs >1000 CPUs limited to windows:
  * Weekdays: 00:00-08:00 only
  * Weekends: Any time
- Benefits:
  * Shifts load to off-peak
  * Reduces abandonment triggers by estimated 60%
  * Improves overall user experience
```

### 4. User Education and Outreach

**Question:** Which users should we contact about their submission patterns?

**Approach:**
1. Sort `user_impact_patterns.csv` by `abandonment_trigger_rate_pct`
2. Filter for `is_regular_pattern == True`
3. Prepare user-specific reports with their impact data

**Example User Report:**

```
To: user_0042
Subject: Optimizing Your HPC Job Submissions

Hello,

We've analyzed cluster usage patterns and identified an opportunity to
improve your job performance and reduce wait times for everyone.

Your Current Pattern:
- You typically submit large jobs (avg 1245 CPUs) on Tuesday evenings
- These jobs trigger increased wait times for all users (+85% avg)
- Submission rate drops 38% cluster-wide when your jobs start

Impact on You:
- Your jobs likely wait longer due to increased competition
- Your own subsequent jobs face higher queue times

Recommendation:
- Submit large jobs during off-peak hours (weekends, weekday nights)
- Consider splitting jobs >1000 CPUs into smaller batches
- Use job arrays for parallel, independent tasks

Benefits:
- Your jobs start faster
- Better cluster experience for everyone
- Same total compute, better scheduling

Would you like to schedule a consultation to discuss optimization strategies?
```

### 5. Testing "What If" Scenarios

**Question:** What if we implement a large job queue with limited hours?

**Approach:**
1. Export data from `high_impact_jobs.csv` and `impact_events.csv`
2. Filter to proposed restricted hours
3. Calculate reduction in abandonment triggers

**Example Analysis:**
```python
import pandas as pd

events = pd.read_csv('impact_events.csv')

# Current state
total_events = len(events)
abandonment_triggers = events[events['is_abandonment_trigger']].shape[0]
current_rate = abandonment_triggers / total_events * 100

print(f"Current abandonment trigger rate: {current_rate:.1f}%")

# What if large jobs restricted to 00:00-08:00?
events['hour'] = pd.to_datetime(events['impact_time']).dt.hour
restricted_hours = events[(events['hour'] >= 0) & (events['hour'] < 8)]

if_restricted = len(restricted_hours[restricted_hours['is_abandonment_trigger']])
reduced_rate = if_restricted / total_events * 100

print(f"Projected abandonment rate with policy: {reduced_rate:.1f}%")
print(f"Reduction: {current_rate - reduced_rate:.1f} percentage points")
print(f"Estimated improvement: {(current_rate - reduced_rate) / current_rate * 100:.0f}%")
```

---

## Advanced Analysis

### Combining with Other Tools

#### Cross-Reference with Wait Time Analysis

```bash
# Run both analyses
python3 analyze_cross_user_impacts.py jobs_anon.csv cluster_config.csv
python3 analyze_queue_wait_times.py jobs_anon.csv

# Combine results
python3 << EOF
import pandas as pd

# Load impact events
impacts = pd.read_csv('impact_events.csv')
impacts['date'] = pd.to_datetime(impacts['impact_time']).dt.date

# Load wait time series
waits = pd.read_csv('wait_times_timeseries.csv')
waits['date'] = pd.to_datetime(waits['date']).dt.date

# Merge
merged = impacts.merge(waits, on='date', how='inner')

# Find correlation
correlation = merged['submit_rate_change_pct'].corr(merged['median_wait_minutes'])
print(f"Correlation between submission rate change and wait times: {correlation:.3f}")

# High impact days
high_impact = merged[merged['is_abandonment_trigger'] == True]
print(f"\nAverage wait time on abandonment trigger days: {high_impact['median_wait_minutes'].mean():.1f} min")
print(f"Average wait time on normal days: {merged[merged['is_abandonment_trigger'] == False]['median_wait_minutes'].mean():.1f} min")
EOF
```

#### Cross-Reference with Heavy-Tailed Jobs

```bash
# Combine heavy-tail and impact analyses
python3 << EOF
import pandas as pd

heavy_tail = pd.read_csv('heavy_tail_by_user.csv')
patterns = pd.read_csv('user_impact_patterns.csv')

combined = heavy_tail.merge(patterns, on='user', how='inner')

# Do heavy-tail users cause more impact?
print("Correlation between heavy-tail job count and abandonment trigger rate:")
print(combined[['user', 'heavy_tail_job_count', 'abandonment_trigger_rate_pct']].corr())

# Top 10 heavy-tail users and their impact
top = combined.nlargest(10, 'heavy_tail_job_count')
print("\nTop Heavy-Tail Users and Their Impact:")
print(top[['user', 'heavy_tail_job_count', 'abandonment_trigger_rate_pct',
           'most_common_day', 'avg_cpus']])
EOF
```

### Visualization

#### Impact Events Timeline

```python
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

df = pd.read_csv('impact_events.csv')
df['impact_time'] = pd.to_datetime(df['impact_time'])
df = df.sort_values('impact_time')

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)

# Submission rate changes over time
colors = ['red' if x else 'blue' for x in df['is_abandonment_trigger']]
ax1.scatter(df['impact_time'], df['submit_rate_change_pct'],
           c=colors, alpha=0.5, s=20)
ax1.axhline(y=-25, color='red', linestyle='--', linewidth=1, label='Abandonment threshold')
ax1.set_ylabel('Submission Rate Change (%)')
ax1.set_title('Impact Events: Submission Rate Changes Over Time')
ax1.legend(['Abandonment threshold', 'Trigger event', 'Normal event'])
ax1.grid(True, alpha=0.3)

# Wait time changes over time
ax2.scatter(df['impact_time'], df['wait_time_change_pct'],
           c=colors, alpha=0.5, s=20)
ax2.set_ylabel('Wait Time Change (%)')
ax2.set_xlabel('Date')
ax2.grid(True, alpha=0.3)

ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.xticks(rotation=45, ha='right')

plt.tight_layout()
plt.savefig('impact_events_timeline.png', dpi=300, bbox_inches='tight')
print("Saved: impact_events_timeline.png")
```

#### User Impact Heatmap

```python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

patterns = pd.read_csv('user_impact_patterns.csv')

# Create day-of-week vs hour-of-day heatmap for top users
top_users = patterns.nlargest(20, 'abandonment_trigger_rate_pct')

fig, ax = plt.subplots(figsize=(10, 8))

# Create matrix: rows = users, columns = days
days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
matrix = []
labels = []

for _, user in top_users.iterrows():
    row = [0] * 7
    day_idx = days.index(user['most_common_day']) if user['most_common_day'] in days else 0
    row[day_idx] = user['abandonment_trigger_rate_pct']
    matrix.append(row)
    labels.append(user['user'])

im = ax.imshow(matrix, aspect='auto', cmap='Reds')

ax.set_xticks(np.arange(7))
ax.set_yticks(np.arange(len(labels)))
ax.set_xticklabels(days)
ax.set_yticklabels(labels)

plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

ax.set_title('User Impact Patterns by Day of Week\n(Abandonment Trigger Rate %)')
fig.colorbar(im, ax=ax, label='Abandonment Trigger Rate (%)')

plt.tight_layout()
plt.savefig('user_impact_heatmap.png', dpi=300, bbox_inches='tight')
print("Saved: user_impact_heatmap.png")
```

---

## Troubleshooting

### "No impact events with sufficient data"

**Issue:** Not enough jobs in before/after windows

**Solutions:**
1. Increase dataset size (longer time range)
2. Adjust window sizes in script (currently 1hr before, 2hr after)
3. Lower minimum job threshold (currently 5 jobs per window)

### "No abandonment triggers found"

**Possible reasons:**
1. Cluster is overprovisioned (queue never gets long)
2. Users don't react to congestion
3. Analysis thresholds too strict

**Solutions:**
- Lower abandonment thresholds (currently -25% submission, -20% users)
- Check `impact_events.csv` for trends even without triggers
- Review wait time data - is there congestion?

### High memory usage

**Issue:** Analyzing millions of jobs

**Solutions:**
1. Script samples top 1000 impact events by default
2. Filter input data by date range first
3. Increase sample size parameter if needed:
   ```python
   # In analyze_cross_user_impacts.py, line ~175
   sample_size = min(5000, len(high_impact_jobs))  # Increase from 1000
   ```

---

## Performance Tips

### Large Datasets (>1M jobs)

**Optimize:**
```bash
# Pre-filter to date range
python3 << EOF
import pandas as pd
df = pd.read_csv('jobs_anon.csv', parse_dates=['submit_time'])
df = df[(df['submit_time'] >= '2024-01-01') & (df['submit_time'] <= '2024-12-31')]
df.to_csv('jobs_2024.csv', index=False)
EOF

# Run analysis on filtered data
python3 analyze_cross_user_impacts.py jobs_2024.csv cluster_config.csv
```

### Focus on Specific Users

```python
# Modify impact_events analysis to focus on specific users
import pandas as pd

df = pd.read_csv('jobs_anon.csv')
high_impact = pd.read_csv('high_impact_jobs.csv')

# Focus on top 50 most impactful users
top_users = high_impact.groupby('user')['impact_score'].mean().nlargest(50).index
focused = high_impact[high_impact['user'].isin(top_users)]

focused.to_csv('high_impact_focused.csv', index=False)
```

---

## Related Documentation

- **[README.md](README.md)** - Main toolkit overview
- **[UTILIZATION_ANALYSIS_GUIDE.md](UTILIZATION_ANALYSIS_GUIDE.md)** - Utilization analysis
- **[COMPLETE_TOOLKIT_SUMMARY.md](COMPLETE_TOOLKIT_SUMMARY.md)** - All tools reference
- **[OSCAR_Cluster_Analysis.md](OSCAR_Cluster_Analysis.md)** - Example analysis

---

## Summary

This cross-user impact analysis enables you to:

✅ **Identify specific incidents** where one user impacts others
✅ **Detect recurring patterns** (e.g., "User X every Tuesday")
✅ **Measure causal relationships** (before/after comparisons)
✅ **Find submission abandonment triggers** (>25% submission drop)
✅ **Understand group dynamics** (how groups affect each other)
✅ **Design targeted policies** (based on real impact data)
✅ **Contact problematic users** (with data-driven recommendations)

**Start analyzing:**
```bash
python3 analyze_cross_user_impacts.py jobs_anonymized.csv cluster_config.csv
```
