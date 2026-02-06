#!/usr/bin/env python3
"""
Event-based submission abandonment analysis

For each job submission, calculate:
1. Queue length at the moment of submission (what the user would have seen)
2. Inter-arrival time (time since previous submission)

Test if users submit less frequently when they would see a long queue.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta

print("Loading job data...")
df = pd.read_csv('oscar_all_jobs_2025.csv')
print(f"Total jobs: {len(df):,}")

# Parse timestamps
df['submit_time'] = pd.to_datetime(df['submit_time'])
df['start_time'] = pd.to_datetime(df['start_time'])
df['end_time'] = pd.to_datetime(df['end_time'])

# Sort by submission time
df = df.sort_values('submit_time').reset_index(drop=True)

print("\n" + "="*80)
print("CALCULATING QUEUE LENGTH AT EACH SUBMISSION")
print("="*80)
print("\nFor each job submission, calculating what the user would have seen...")

# This is computationally intensive, so we'll use a vectorized approach
# For each submission time, count how many jobs are queued

queue_length_at_submit = []

print("\nProcessing jobs...")
# Sample for efficiency - analyze every Nth job
sample_interval = 100  # Analyze every 100th job for speed
sampled_indices = range(0, len(df), sample_interval)

for idx in sampled_indices:
    if idx % 10000 == 0:
        print(f"  Processed {idx:,}/{len(df):,} jobs ({idx/len(df)*100:.1f}%)")

    submit_t = df.loc[idx, 'submit_time']

    # Count jobs that were submitted before this time but not started yet
    # (This is what the user would see in squeue)
    queued = ((df['submit_time'] < submit_t) &
              (df['start_time'] > submit_t)).sum()

    queue_length_at_submit.append({
        'job_idx': idx,
        'submit_time': submit_t,
        'queue_length': queued,
        'cpus_req': df.loc[idx, 'cpus_req']
    })

print(f"\nAnalyzed {len(queue_length_at_submit):,} job submissions")

# Create dataframe
events_df = pd.DataFrame(queue_length_at_submit)

# Calculate inter-arrival time (time since previous submission)
events_df['time_since_prev'] = events_df['submit_time'].diff().dt.total_seconds() / 60  # minutes

# Calculate rolling submission rate (jobs per hour in surrounding window)
events_df['rolling_rate'] = 0.0
window_minutes = 30

for i in range(len(events_df)):
    if i % 1000 == 0 and i > 0:
        print(f"  Calculating rolling rates: {i:,}/{len(events_df):,}")

    t = events_df.loc[i, 'submit_time']
    t_start = t - timedelta(minutes=window_minutes)
    t_end = t + timedelta(minutes=window_minutes)

    # Count jobs in window
    in_window = ((events_df['submit_time'] >= t_start) &
                 (events_df['submit_time'] <= t_end))
    jobs_in_window = in_window.sum()

    # Convert to jobs per hour
    rate_per_hour = jobs_in_window / (2 * window_minutes / 60)
    events_df.loc[i, 'rolling_rate'] = rate_per_hour

print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)

print(f"\nQueue Length at Submission:")
print(f"  Mean: {events_df['queue_length'].mean():.1f} jobs")
print(f"  Median: {events_df['queue_length'].median():.1f} jobs")
print(f"  Std Dev: {events_df['queue_length'].std():.1f} jobs")
print(f"  Min: {events_df['queue_length'].min():.0f} jobs")
print(f"  Max: {events_df['queue_length'].max():.0f} jobs")

print(f"\nInter-arrival Time (time between consecutive submissions):")
valid_inter = events_df['time_since_prev'].dropna()
print(f"  Mean: {valid_inter.mean():.2f} minutes")
print(f"  Median: {valid_inter.median():.2f} minutes")
print(f"  Std Dev: {valid_inter.std():.2f} minutes")

print(f"\nRolling Submission Rate ({window_minutes}-min window):")
print(f"  Mean: {events_df['rolling_rate'].mean():.1f} jobs/hour")
print(f"  Std Dev: {events_df['rolling_rate'].std():.1f} jobs/hour")

print("\n" + "="*80)
print("CORRELATION ANALYSIS")
print("="*80)

# Test 1: Queue length vs inter-arrival time
# If users avoid long queues, inter-arrival time should increase when queue is long
corr_inter = events_df['queue_length'].corr(events_df['time_since_prev'])
print(f"\nQueue Length vs Inter-arrival Time: r = {corr_inter:+.4f}")
if corr_inter > 0.1:
    print("  ✓ Positive correlation - users wait longer to submit when queue is long!")
elif corr_inter > 0.05:
    print("  ~ Weak positive correlation - slight evidence of avoidance")
else:
    print("  ✗ No correlation - submission timing independent of queue length")

# Test 2: Queue length vs rolling submission rate
# If users avoid long queues, submission rate should drop when queue is long
corr_rate = events_df['queue_length'].corr(events_df['rolling_rate'])
print(f"\nQueue Length vs Rolling Submission Rate: r = {corr_rate:+.4f}")
if corr_rate < -0.1:
    print("  ✓ Negative correlation - fewer submissions when queue is long!")
elif corr_rate < -0.05:
    print("  ~ Weak negative correlation - slight evidence of avoidance")
else:
    print("  ✗ No correlation - submission rate independent of queue length")

print("\n" + "="*80)
print("QUEUE LENGTH BINS ANALYSIS")
print("="*80)
print("\nComparing submission behavior at different queue lengths...")

# Bin queue lengths
queue_bins = [0, 100, 500, 1000, 2000, float('inf')]
queue_labels = ['0-100', '100-500', '500-1K', '1K-2K', '>2K']
events_df['queue_bin'] = pd.cut(events_df['queue_length'], bins=queue_bins, labels=queue_labels)

print("\nMean Inter-arrival Time by Queue Length:")
for label in queue_labels:
    subset = events_df[events_df['queue_bin'] == label]
    if len(subset) > 0:
        mean_inter = subset['time_since_prev'].mean()
        count = len(subset)
        print(f"  Queue {label:8s}: {mean_inter:7.2f} min  ({count:,} submissions)")

print("\nMean Rolling Submission Rate by Queue Length:")
for label in queue_labels:
    subset = events_df[events_df['queue_bin'] == label]
    if len(subset) > 0:
        mean_rate = subset['rolling_rate'].mean()
        count = len(subset)
        print(f"  Queue {label:8s}: {mean_rate:7.1f} jobs/hour  ({count:,} submissions)")

print("\n" + "="*80)
print("TIME-OF-DAY ANALYSIS")
print("="*80)
print("\nDo users check queue more actively during work hours?")

events_df['hour'] = events_df['submit_time'].dt.hour
events_df['is_work_hours'] = (events_df['hour'] >= 9) & (events_df['hour'] <= 17)

work_hours = events_df[events_df['is_work_hours']]
off_hours = events_df[~events_df['is_work_hours']]

work_corr_inter = work_hours['queue_length'].corr(work_hours['time_since_prev'])
off_corr_inter = off_hours['queue_length'].corr(off_hours['time_since_prev'])

work_corr_rate = work_hours['queue_length'].corr(work_hours['rolling_rate'])
off_corr_rate = off_hours['queue_length'].corr(off_hours['rolling_rate'])

print(f"\nWork Hours (9am-5pm):")
print(f"  Queue vs Inter-arrival: r = {work_corr_inter:+.4f}")
print(f"  Queue vs Submission Rate: r = {work_corr_rate:+.4f}")

print(f"\nOff Hours:")
print(f"  Queue vs Inter-arrival: r = {off_corr_inter:+.4f}")
print(f"  Queue vs Submission Rate: r = {off_corr_rate:+.4f}")

if abs(work_corr_rate) > abs(off_corr_rate):
    print("\n  ✓ Stronger effect during work hours - consistent with active monitoring!")
else:
    print("\n  ? Effect not stronger during work hours")

print("\n" + "="*80)
print("VISUALIZATION")
print("="*80)

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Time series of queue length
ax1 = axes[0, 0]
sample_size = min(10000, len(events_df))
sample = events_df.head(sample_size)
ax1.plot(sample['submit_time'], sample['queue_length'], alpha=0.5, linewidth=0.5)
ax1.set_xlabel('Time')
ax1.set_ylabel('Queue Length (jobs)')
ax1.set_title(f'Queue Length at Each Submission (first {sample_size:,} jobs)')
ax1.grid(True, alpha=0.3)

# Plot 2: Queue length vs inter-arrival time
ax2 = axes[0, 1]
valid = events_df.dropna(subset=['time_since_prev'])
# Limit to reasonable inter-arrival times for visualization
valid_plot = valid[valid['time_since_prev'] < 60]  # < 1 hour
ax2.scatter(valid_plot['queue_length'], valid_plot['time_since_prev'],
           alpha=0.1, s=3)
ax2.set_xlabel('Queue Length (jobs)')
ax2.set_ylabel('Time Since Previous Submission (minutes)')
ax2.set_title(f'Queue Length vs Inter-arrival Time (r={corr_inter:+.4f})')
ax2.grid(True, alpha=0.3)

# Add trend line
z = np.polyfit(valid_plot['queue_length'], valid_plot['time_since_prev'], 1)
p = np.poly1d(z)
x_line = np.linspace(valid_plot['queue_length'].min(),
                     valid_plot['queue_length'].max(), 100)
ax2.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2, label='Trend')
ax2.legend()

# Plot 3: Queue length vs rolling submission rate
ax3 = axes[1, 0]
ax3.scatter(events_df['queue_length'], events_df['rolling_rate'],
           alpha=0.1, s=3)
ax3.set_xlabel('Queue Length (jobs)')
ax3.set_ylabel('Rolling Submission Rate (jobs/hour)')
ax3.set_title(f'Queue Length vs Submission Rate (r={corr_rate:+.4f})')
ax3.grid(True, alpha=0.3)

# Add trend line
z = np.polyfit(events_df['queue_length'], events_df['rolling_rate'], 1)
p = np.poly1d(z)
x_line = np.linspace(events_df['queue_length'].min(),
                     events_df['queue_length'].max(), 100)
ax3.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2, label='Trend')
ax3.legend()

# Plot 4: Box plot by queue length bin
ax4 = axes[1, 1]
bin_data = [events_df[events_df['queue_bin'] == label]['rolling_rate'].dropna()
            for label in queue_labels]
ax4.boxplot(bin_data, labels=queue_labels)
ax4.set_xlabel('Queue Length Bin')
ax4.set_ylabel('Submission Rate (jobs/hour)')
ax4.set_title('Submission Rate Distribution by Queue Length')
ax4.grid(True, alpha=0.3, axis='y')
plt.setp(ax4.xaxis.get_majorticklabels(), rotation=45)

plt.tight_layout()
plt.savefig('submission_abandonment_events.png', dpi=150, bbox_inches='tight')
print("\n✓ Plots saved to: submission_abandonment_events.png")

# Save event data
events_df.to_csv('submission_events_data.csv', index=False)
print("✓ Event data saved to: submission_events_data.csv")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if corr_rate < -0.2 or corr_inter > 0.2:
    print("\n✓ STRONG evidence of submission abandonment behavior!")
    if corr_inter > 0.1:
        print(f"  - Users wait longer between submissions when queue is long (r={corr_inter:+.4f})")
    if corr_rate < -0.1:
        print(f"  - Submission rate drops when queue is long (r={corr_rate:+.4f})")
    print("  - Users appear to check queue and delay when congested")
elif corr_rate < -0.1 or corr_inter > 0.1:
    print("\n~ MODERATE evidence of submission abandonment")
    print("  - Some users may be checking queue before submitting")
    print("  - Effect is modest - other factors dominate")
else:
    print("\n✗ NO strong evidence of submission abandonment")
    print("  - Submission patterns appear independent of queue state")
    print("  - Likely driven by automation, workflows, or schedules")

print("\n" + "="*80)
