#!/usr/bin/env python3
"""
Analyze submission abandonment behavior - do users avoid submitting when queue is long?

Hypothesis: Users check queue length before submitting. When they see a long queue,
they delay submission, causing submission rate to drop. This creates oscillating
submission patterns with negative correlation between queue length and future submissions.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

print("Loading job data...")
df = pd.read_csv('oscar_all_jobs_2025.csv')

print(f"Total jobs: {len(df):,}")

# Parse timestamps
df['submit_time'] = pd.to_datetime(df['submit_time'])
df['start_time'] = pd.to_datetime(df['start_time'])
df['end_time'] = pd.to_datetime(df['end_time'])

# Calculate queue wait time
df['queue_time_hours'] = (df['start_time'] - df['submit_time']).dt.total_seconds() / 3600

print("\nGenerating hourly time series...")

# Create hourly time points covering the full period
start_time = df['submit_time'].min()
end_time = df['submit_time'].max()
time_points = pd.date_range(start=start_time, end=end_time, freq='1h')

print(f"Time range: {start_time} to {end_time}")
print(f"Total time points: {len(time_points):,} hours")

# Calculate metrics at each time point
submission_rate = []  # Jobs submitted per hour
queue_length = []     # Jobs waiting in queue
avg_queue_time = []   # Average wait time for jobs in queue
concurrent_jobs = []  # Jobs currently running

print("\nSampling time series (this will take a few minutes)...")
for i, t in enumerate(time_points):
    if i % 1000 == 0:
        print(f"  Processed {i:,}/{len(time_points):,} time points...")

    # Submission rate: jobs submitted in the hour before time t
    t_minus_1h = t - pd.Timedelta(hours=1)
    submitted = df[(df['submit_time'] >= t_minus_1h) & (df['submit_time'] < t)]
    submission_rate.append(len(submitted))

    # Queue length: jobs submitted but not yet started at time t
    queued = df[(df['submit_time'] <= t) & (df['start_time'] > t)]
    queue_length.append(len(queued))

    # Average queue time for jobs currently in queue
    if len(queued) > 0:
        avg_wait = queued['queue_time_hours'].mean()
        avg_queue_time.append(avg_wait)
    else:
        avg_queue_time.append(0)

    # Concurrent running jobs
    running = df[(df['start_time'] <= t) & (df['end_time'] > t)]
    concurrent_jobs.append(len(running))

print("Time series generation complete!")

# Create dataframe
ts_df = pd.DataFrame({
    'time': time_points,
    'submission_rate': submission_rate,
    'queue_length': queue_length,
    'avg_queue_time': avg_queue_time,
    'concurrent_jobs': concurrent_jobs
})

# Add time features
ts_df['hour_of_day'] = ts_df['time'].dt.hour
ts_df['day_of_week'] = ts_df['time'].dt.dayofweek
ts_df['is_work_hours'] = (ts_df['hour_of_day'] >= 9) & (ts_df['hour_of_day'] <= 17)
ts_df['is_weekday'] = ts_df['day_of_week'] < 5

print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)

print(f"\nSubmission Rate (jobs/hour):")
print(f"  Mean: {ts_df['submission_rate'].mean():.1f} jobs/hour")
print(f"  Median: {ts_df['submission_rate'].median():.1f} jobs/hour")
print(f"  Std Dev: {ts_df['submission_rate'].std():.1f} jobs/hour")
print(f"  Min: {ts_df['submission_rate'].min():.0f} jobs/hour")
print(f"  Max: {ts_df['submission_rate'].max():.0f} jobs/hour")

print(f"\nQueue Length (jobs waiting):")
print(f"  Mean: {ts_df['queue_length'].mean():.1f} jobs")
print(f"  Median: {ts_df['queue_length'].median():.1f} jobs")
print(f"  Std Dev: {ts_df['queue_length'].std():.1f} jobs")
print(f"  Min: {ts_df['queue_length'].min():.0f} jobs")
print(f"  Max: {ts_df['queue_length'].max():.0f} jobs")

print(f"\nConcurrent Running Jobs:")
print(f"  Mean: {ts_df['concurrent_jobs'].mean():.1f} jobs")
print(f"  Max: {ts_df['concurrent_jobs'].max():.0f} jobs")

print("\n" + "="*80)
print("LAG CORRELATION ANALYSIS")
print("="*80)
print("\nTesting if high queue length predicts low submission rate in the future...")

# Test various lags (0 to 24 hours)
lags = [0, 1, 2, 3, 4, 6, 8, 12, 24]
correlations = []

print("\nCorrelation between Queue Length at time T and Submission Rate at time T+lag:")
print("(Negative correlation = users avoid submitting when queue is long)")
print()

for lag in lags:
    # Shift submission rate forward by lag hours
    lagged_submission = ts_df['submission_rate'].shift(-lag)

    # Correlate with current queue length
    corr = ts_df['queue_length'].corr(lagged_submission)
    correlations.append(corr)

    significance = ""
    if abs(corr) > 0.3:
        significance = " *** STRONG"
    elif abs(corr) > 0.2:
        significance = " ** MODERATE"
    elif abs(corr) > 0.1:
        significance = " * WEAK"

    print(f"  Lag {lag:2d} hours: r = {corr:+.4f}{significance}")

# Find optimal lag (most negative correlation)
optimal_lag_idx = np.argmin(correlations)
optimal_lag = lags[optimal_lag_idx]
optimal_corr = correlations[optimal_lag_idx]

print(f"\nOptimal lag: {optimal_lag} hours (r = {optimal_corr:+.4f})")

if optimal_corr < -0.1:
    print("\n✓ Evidence of submission abandonment behavior!")
    print(f"  When queue is long, users reduce submissions {optimal_lag} hours later")
else:
    print("\n✗ No strong evidence of submission abandonment")
    print("  Submission patterns may be driven by other factors (time of day, workflows)")

print("\n" + "="*80)
print("WORK HOURS vs OFF-HOURS COMPARISON")
print("="*80)
print("\nTesting if abandonment effect is stronger during work hours...")
print("(Users actively monitor queue during work hours)")

# Split by work hours
work_hours = ts_df[ts_df['is_work_hours']]
off_hours = ts_df[~ts_df['is_work_hours']]

# Calculate correlation at optimal lag for each
if len(work_hours) > optimal_lag and len(off_hours) > optimal_lag:
    work_lagged = work_hours['submission_rate'].shift(-optimal_lag)
    work_corr = work_hours['queue_length'].corr(work_lagged)

    off_lagged = off_hours['submission_rate'].shift(-optimal_lag)
    off_corr = off_hours['queue_length'].corr(off_lagged)

    print(f"\nWork hours (9am-5pm):  r = {work_corr:+.4f}")
    print(f"Off hours:             r = {off_corr:+.4f}")

    if abs(work_corr) > abs(off_corr):
        print("\n✓ Stronger effect during work hours - consistent with active monitoring!")
    else:
        print("\n? Effect not stronger during work hours - may be driven by other factors")

print("\n" + "="*80)
print("OSCILLATION PATTERN ANALYSIS")
print("="*80)
print("\nLooking for periodic cycles in submission rate...")

# Calculate autocorrelation of submission rate
from pandas.plotting import autocorrelation_plot

# Detrend by removing daily pattern
ts_df['hour'] = ts_df['time'].dt.hour
hourly_mean = ts_df.groupby('hour')['submission_rate'].transform('mean')
ts_df['submission_detrended'] = ts_df['submission_rate'] - hourly_mean

# Check for periodicity
print("\nAutocorrelation of submission rate (detrended):")
acf_lags = [1, 2, 4, 6, 12, 24, 48]
for lag in acf_lags:
    acf = ts_df['submission_detrended'].autocorr(lag=lag)
    print(f"  Lag {lag:3d} hours: {acf:+.4f}")

print("\n" + "="*80)
print("EXTREME QUEUE EVENTS")
print("="*80)
print("\nAnalyzing what happens after extreme queue buildup...")

# Find times when queue was extremely long
queue_95th = ts_df['queue_length'].quantile(0.95)
extreme_queue = ts_df[ts_df['queue_length'] >= queue_95th]

print(f"\nQueue 95th percentile: {queue_95th:.0f} jobs")
print(f"Number of extreme queue events: {len(extreme_queue):,}")

if len(extreme_queue) > 0:
    # Look at submission rate 1-6 hours after extreme queue
    print("\nMean submission rate after extreme queue events:")
    for lag in [1, 2, 3, 4, 6]:
        indices = extreme_queue.index + lag
        valid_indices = indices[indices < len(ts_df)]
        if len(valid_indices) > 0:
            mean_sub = ts_df.loc[valid_indices, 'submission_rate'].mean()
            overall_mean = ts_df['submission_rate'].mean()
            pct_change = (mean_sub - overall_mean) / overall_mean * 100
            print(f"  {lag} hours later: {mean_sub:.1f} jobs/hour ({pct_change:+.1f}% vs mean)")

print("\n" + "="*80)
print("VISUALIZATION")
print("="*80)

# Create plots
fig, axes = plt.subplots(4, 1, figsize=(14, 12))

# Plot 1: Submission rate and queue length over time (first 30 days)
sample_days = 30
sample_hours = sample_days * 24
ax1 = axes[0]
sample_df = ts_df.head(sample_hours)
ax1.plot(sample_df['time'], sample_df['submission_rate'], label='Submission Rate (jobs/hr)', alpha=0.7)
ax1_twin = ax1.twinx()
ax1_twin.plot(sample_df['time'], sample_df['queue_length'],
              color='red', label='Queue Length', alpha=0.7)
ax1.set_xlabel('Time')
ax1.set_ylabel('Submission Rate (jobs/hour)', color='blue')
ax1_twin.set_ylabel('Queue Length (jobs)', color='red')
ax1.set_title(f'Submission Rate vs Queue Length (First {sample_days} Days)')
ax1.grid(True, alpha=0.3)
ax1.legend(loc='upper left')
ax1_twin.legend(loc='upper right')

# Plot 2: Lag correlation
ax2 = axes[1]
ax2.bar(lags, correlations, alpha=0.7, color=['red' if c < 0 else 'blue' for c in correlations])
ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
ax2.axhline(y=-0.1, color='red', linestyle='--', linewidth=0.5, alpha=0.5, label='Weak threshold')
ax2.axhline(y=-0.2, color='red', linestyle='--', linewidth=1.0, alpha=0.7, label='Moderate threshold')
ax2.set_xlabel('Lag (hours)')
ax2.set_ylabel('Correlation Coefficient')
ax2.set_title('Correlation: Queue Length(T) vs Submission Rate(T+lag)')
ax2.grid(True, alpha=0.3)
ax2.legend()

# Plot 3: Distribution comparison
ax3 = axes[2]
bins = 50
ax3.hist(ts_df['submission_rate'], bins=bins, alpha=0.7, label='Submission Rate', density=True)
ax3.set_xlabel('Jobs per hour')
ax3.set_ylabel('Density')
ax3.set_title('Distribution of Submission Rate')
ax3.grid(True, alpha=0.3)
ax3.legend()

# Plot 4: Scatter plot at optimal lag
ax4 = axes[3]
lagged_submission = ts_df['submission_rate'].shift(-optimal_lag)
valid_idx = ~lagged_submission.isna()
ax4.scatter(ts_df.loc[valid_idx, 'queue_length'],
           lagged_submission[valid_idx],
           alpha=0.1, s=5)
ax4.set_xlabel('Queue Length (jobs)')
ax4.set_ylabel(f'Submission Rate {optimal_lag}h later (jobs/hour)')
ax4.set_title(f'Queue Length vs Future Submission Rate (lag={optimal_lag}h, r={optimal_corr:.4f})')
ax4.grid(True, alpha=0.3)

# Add trend line
z = np.polyfit(ts_df.loc[valid_idx, 'queue_length'], lagged_submission[valid_idx], 1)
p = np.poly1d(z)
x_line = np.linspace(ts_df['queue_length'].min(), ts_df['queue_length'].max(), 100)
ax4.plot(x_line, p(x_line), "r--", alpha=0.8, linewidth=2, label='Trend line')
ax4.legend()

plt.tight_layout()
plt.savefig('submission_abandonment_analysis.png', dpi=150, bbox_inches='tight')
print("\n✓ Plots saved to: submission_abandonment_analysis.png")

# Save time series data
ts_df.to_csv('time_series_data.csv', index=False)
print("✓ Time series data saved to: time_series_data.csv")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

if optimal_corr < -0.2:
    print("\n✓ STRONG evidence of submission abandonment behavior")
    print(f"  - Queue length negatively correlates with submissions {optimal_lag}h later (r={optimal_corr:.4f})")
    print("  - Users appear to check queue and delay submissions when congested")
    print("  - This creates self-regulating feedback loop in cluster usage")
elif optimal_corr < -0.1:
    print("\n~ WEAK evidence of submission abandonment behavior")
    print(f"  - Modest negative correlation at {optimal_lag}h lag (r={optimal_corr:.4f})")
    print("  - Effect may exist but is small compared to other factors")
else:
    print("\n✗ NO strong evidence of submission abandonment")
    print("  - Submission patterns appear independent of queue state")
    print("  - Likely driven by work schedules, workflows, or deadlines")

print("\n" + "="*80)
