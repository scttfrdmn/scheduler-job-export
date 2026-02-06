#!/usr/bin/env python3
"""
Queue Wait Time Analysis

Analyzes job queue wait times with comprehensive statistics:
- Per-user and per-group aggregates
- Temporal patterns (time of day, day of week, weekly, monthly)
- Queue depth correlation
- Fair share effectiveness

Outputs time series and statistical summaries for:
- Identifying best submission times
- Understanding queue dynamics
- Evaluating scheduling fairness
"""

import pandas as pd
import numpy as np
import sys
from datetime import datetime

def load_job_data(filename):
    """Load job data with timing information"""
    print(f"Loading job data from {filename}...")

    df = pd.read_csv(filename)

    # Parse timestamps
    for col in ['submit_time', 'start_time', 'end_time']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Calculate wait time (submit to start)
    if 'submit_time' in df.columns and 'start_time' in df.columns:
        df['wait_time_seconds'] = (df['start_time'] - df['submit_time']).dt.total_seconds()
        df['wait_time_minutes'] = df['wait_time_seconds'] / 60
        df['wait_time_hours'] = df['wait_time_seconds'] / 3600

        # Remove invalid wait times
        df = df[df['wait_time_seconds'] >= 0]

        print(f"  Calculated wait times for {len(df):,} jobs")
    else:
        print("  ERROR: Missing submit_time or start_time columns")
        sys.exit(1)

    # Parse resource columns
    if 'cpus' in df.columns:
        df['cpus'] = pd.to_numeric(df['cpus'], errors='coerce').fillna(1)

    if 'mem_req' in df.columns:
        df['mem_req'] = pd.to_numeric(df['mem_req'], errors='coerce').fillna(0)

    if 'nodes' in df.columns:
        df['nodes'] = pd.to_numeric(df['nodes'], errors='coerce').fillna(1)

    # Calculate runtime
    if 'end_time' in df.columns:
        df['runtime_hours'] = (df['end_time'] - df['start_time']).dt.total_seconds() / 3600

    print(f"Loaded {len(df):,} jobs with valid wait times")

    return df

def calculate_overall_statistics(df):
    """Calculate overall wait time statistics"""
    print("\n" + "="*80)
    print("OVERALL WAIT TIME STATISTICS")
    print("="*80)

    wait_times = df['wait_time_minutes']

    print(f"\nAll Jobs (n={len(df):,}):")
    print(f"  Mean wait:       {wait_times.mean():>12.1f} minutes ({wait_times.mean()/60:.1f} hours)")
    print(f"  Median wait:     {wait_times.median():>12.1f} minutes ({wait_times.median()/60:.1f} hours)")
    print(f"  Std deviation:   {wait_times.std():>12.1f} minutes")
    print(f"  Min wait:        {wait_times.min():>12.1f} minutes")
    print(f"  Max wait:        {wait_times.max():>12.1f} minutes ({wait_times.max()/60:.1f} hours)")
    print(f"  25th percentile: {wait_times.quantile(0.25):>12.1f} minutes")
    print(f"  75th percentile: {wait_times.quantile(0.75):>12.1f} minutes")
    print(f"  90th percentile: {wait_times.quantile(0.90):>12.1f} minutes ({wait_times.quantile(0.90)/60:.1f} hours)")
    print(f"  95th percentile: {wait_times.quantile(0.95):>12.1f} minutes ({wait_times.quantile(0.95)/60:.1f} hours)")
    print(f"  99th percentile: {wait_times.quantile(0.99):>12.1f} minutes ({wait_times.quantile(0.99)/60:.1f} hours)")

    # Distribution by wait time bins
    print("\nDistribution by wait time:")
    bins = [0, 1, 5, 15, 30, 60, 120, 240, 480, 1440, float('inf')]
    labels = ['<1min', '1-5min', '5-15min', '15-30min', '30-60min', '1-2hr', '2-4hr', '4-8hr', '8-24hr', '>24hr']
    df['wait_bin'] = pd.cut(df['wait_time_minutes'], bins=bins, labels=labels)

    for label in labels:
        count = (df['wait_bin'] == label).sum()
        pct = count / len(df) * 100
        print(f"  {label:10s}: {count:>8,} jobs ({pct:>5.1f}%)")

    print("\n" + "="*80)

def analyze_per_user(df):
    """Analyze wait times per user"""
    print("\nAnalyzing per-user wait times...")

    if 'user' not in df.columns:
        print("  Warning: No 'user' column found")
        return None

    user_stats = []

    for user in df['user'].unique():
        if pd.isna(user):
            continue

        user_jobs = df[df['user'] == user]

        stats = {
            'user': user,
            'total_jobs': len(user_jobs),
            'wait_mean_minutes': user_jobs['wait_time_minutes'].mean(),
            'wait_median_minutes': user_jobs['wait_time_minutes'].median(),
            'wait_std_minutes': user_jobs['wait_time_minutes'].std(),
            'wait_p90_minutes': user_jobs['wait_time_minutes'].quantile(0.90),
            'wait_p95_minutes': user_jobs['wait_time_minutes'].quantile(0.95),
            'wait_max_minutes': user_jobs['wait_time_minutes'].max(),
            'jobs_wait_under_5min': (user_jobs['wait_time_minutes'] < 5).sum(),
            'jobs_wait_over_1hr': (user_jobs['wait_time_minutes'] > 60).sum(),
            'jobs_wait_over_1day': (user_jobs['wait_time_minutes'] > 1440).sum(),
        }

        # Calculate total CPU-hours waited
        if 'cpus' in user_jobs.columns:
            stats['total_cpu_hours_waited'] = (user_jobs['wait_time_hours'] * user_jobs['cpus']).sum()

        user_stats.append(stats)

    user_df = pd.DataFrame(user_stats)
    user_df = user_df.sort_values('total_jobs', ascending=False)

    print(f"  Analyzed {len(user_df)} users")

    return user_df

def analyze_per_group(df):
    """Analyze wait times per group"""
    print("\nAnalyzing per-group wait times...")

    if 'group' not in df.columns:
        print("  Warning: No 'group' column found")
        return None

    group_stats = []

    for group in df['group'].unique():
        if pd.isna(group):
            continue

        group_jobs = df[df['group'] == group]

        stats = {
            'group': group,
            'total_jobs': len(group_jobs),
            'unique_users': group_jobs['user'].nunique() if 'user' in group_jobs.columns else 0,
            'wait_mean_minutes': group_jobs['wait_time_minutes'].mean(),
            'wait_median_minutes': group_jobs['wait_time_minutes'].median(),
            'wait_p90_minutes': group_jobs['wait_time_minutes'].quantile(0.90),
            'wait_p95_minutes': group_jobs['wait_time_minutes'].quantile(0.95),
        }

        # Calculate total CPU-hours waited
        if 'cpus' in group_jobs.columns:
            stats['total_cpu_hours_waited'] = (group_jobs['wait_time_hours'] * group_jobs['cpus']).sum()

        group_stats.append(stats)

    group_df = pd.DataFrame(group_stats)
    group_df = group_df.sort_values('total_jobs', ascending=False)

    print(f"  Analyzed {len(group_df)} groups")

    return group_df

def analyze_by_time_of_day(df):
    """Analyze wait times by hour of day"""
    print("\nAnalyzing wait times by time of day...")

    df['submit_hour'] = df['submit_time'].dt.hour

    hourly_stats = []

    for hour in range(24):
        hour_jobs = df[df['submit_hour'] == hour]

        if len(hour_jobs) == 0:
            continue

        stats = {
            'hour': hour,
            'hour_label': f"{hour:02d}:00",
            'total_jobs': len(hour_jobs),
            'wait_mean_minutes': hour_jobs['wait_time_minutes'].mean(),
            'wait_median_minutes': hour_jobs['wait_time_minutes'].median(),
            'wait_p90_minutes': hour_jobs['wait_time_minutes'].quantile(0.90),
        }

        hourly_stats.append(stats)

    hourly_df = pd.DataFrame(hourly_stats)
    hourly_df = hourly_df.sort_values('hour')

    print(f"  Analyzed {len(hourly_df)} hours")

    return hourly_df

def analyze_by_day_of_week(df):
    """Analyze wait times by day of week"""
    print("\nAnalyzing wait times by day of week...")

    df['submit_dayofweek'] = df['submit_time'].dt.dayofweek  # 0=Monday
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    daily_stats = []

    for day_num in range(7):
        day_jobs = df[df['submit_dayofweek'] == day_num]

        if len(day_jobs) == 0:
            continue

        stats = {
            'day_of_week': day_num,
            'day_name': day_names[day_num],
            'total_jobs': len(day_jobs),
            'wait_mean_minutes': day_jobs['wait_time_minutes'].mean(),
            'wait_median_minutes': day_jobs['wait_time_minutes'].median(),
            'wait_p90_minutes': day_jobs['wait_time_minutes'].quantile(0.90),
        }

        daily_stats.append(stats)

    daily_df = pd.DataFrame(daily_stats)
    daily_df = daily_df.sort_values('day_of_week')

    print(f"  Analyzed {len(daily_df)} days of week")

    return daily_df

def analyze_by_week_of_month(df):
    """Analyze wait times by week of month"""
    print("\nAnalyzing wait times by week of month...")

    df['week_of_month'] = (df['submit_time'].dt.day - 1) // 7 + 1

    weekly_stats = []

    for week in range(1, 6):  # Weeks 1-5
        week_jobs = df[df['week_of_month'] == week]

        if len(week_jobs) == 0:
            continue

        stats = {
            'week_of_month': week,
            'week_label': f"Week {week}",
            'total_jobs': len(week_jobs),
            'wait_mean_minutes': week_jobs['wait_time_minutes'].mean(),
            'wait_median_minutes': week_jobs['wait_time_minutes'].median(),
            'wait_p90_minutes': week_jobs['wait_time_minutes'].quantile(0.90),
        }

        weekly_stats.append(stats)

    weekly_df = pd.DataFrame(weekly_stats)
    weekly_df = weekly_df.sort_values('week_of_month')

    print(f"  Analyzed {len(weekly_df)} weeks of month")

    return weekly_df

def analyze_by_month(df):
    """Analyze wait times by month"""
    print("\nAnalyzing wait times by month...")

    df['submit_month'] = df['submit_time'].dt.month
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    monthly_stats = []

    for month_num in range(1, 13):
        month_jobs = df[df['submit_month'] == month_num]

        if len(month_jobs) == 0:
            continue

        stats = {
            'month': month_num,
            'month_name': month_names[month_num - 1],
            'total_jobs': len(month_jobs),
            'wait_mean_minutes': month_jobs['wait_time_minutes'].mean(),
            'wait_median_minutes': month_jobs['wait_time_minutes'].median(),
            'wait_p90_minutes': month_jobs['wait_time_minutes'].quantile(0.90),
        }

        monthly_stats.append(stats)

    monthly_df = pd.DataFrame(monthly_stats)
    monthly_df = monthly_df.sort_values('month')

    print(f"  Analyzed {len(monthly_df)} months")

    return monthly_df

def analyze_over_time(df):
    """Analyze wait times over calendar time"""
    print("\nAnalyzing wait times over calendar time...")

    # Weekly aggregates
    df['week'] = df['submit_time'].dt.to_period('W')

    weekly_timeseries = []

    for week in df['week'].dropna().unique():
        week_jobs = df[df['week'] == week]

        stats = {
            'week_start': week.start_time,
            'week': str(week),
            'total_jobs': len(week_jobs),
            'wait_mean_minutes': week_jobs['wait_time_minutes'].mean(),
            'wait_median_minutes': week_jobs['wait_time_minutes'].median(),
            'wait_p90_minutes': week_jobs['wait_time_minutes'].quantile(0.90),
        }

        weekly_timeseries.append(stats)

    timeseries_df = pd.DataFrame(weekly_timeseries)
    timeseries_df = timeseries_df.sort_values('week_start')

    print(f"  Analyzed {len(timeseries_df)} weeks")

    return timeseries_df

def analyze_by_job_size(df):
    """Analyze wait times by job size (CPUs requested)"""
    print("\nAnalyzing wait times by job size...")

    if 'cpus' not in df.columns:
        print("  Warning: No 'cpus' column found")
        return None

    # Create size bins
    bins = [0, 1, 4, 8, 16, 32, 64, 128, 256, float('inf')]
    labels = ['1', '2-4', '5-8', '9-16', '17-32', '33-64', '65-128', '129-256', '256+']
    df['cpu_bin'] = pd.cut(df['cpus'], bins=bins, labels=labels)

    size_stats = []

    for label in labels:
        size_jobs = df[df['cpu_bin'] == label]

        if len(size_jobs) == 0:
            continue

        stats = {
            'cpu_range': label,
            'total_jobs': len(size_jobs),
            'wait_mean_minutes': size_jobs['wait_time_minutes'].mean(),
            'wait_median_minutes': size_jobs['wait_time_minutes'].median(),
            'wait_p90_minutes': size_jobs['wait_time_minutes'].quantile(0.90),
        }

        size_stats.append(stats)

    size_df = pd.DataFrame(size_stats)

    print(f"  Analyzed {len(size_df)} size categories")

    return size_df

def print_temporal_insights(hourly_df, daily_df, monthly_df):
    """Print insights about best submission times"""
    print("\n" + "="*80)
    print("BEST TIMES TO SUBMIT JOBS")
    print("="*80)

    # Best hour
    if hourly_df is not None and len(hourly_df) > 0:
        best_hour = hourly_df.loc[hourly_df['wait_median_minutes'].idxmin()]
        worst_hour = hourly_df.loc[hourly_df['wait_median_minutes'].idxmax()]

        print(f"\nBy Time of Day:")
        print(f"  Best:  {best_hour['hour_label']} (median wait: {best_hour['wait_median_minutes']:.1f} min)")
        print(f"  Worst: {worst_hour['hour_label']} (median wait: {worst_hour['wait_median_minutes']:.1f} min)")
        print(f"  Difference: {worst_hour['wait_median_minutes'] - best_hour['wait_median_minutes']:.1f} min")

    # Best day
    if daily_df is not None and len(daily_df) > 0:
        best_day = daily_df.loc[daily_df['wait_median_minutes'].idxmin()]
        worst_day = daily_df.loc[daily_df['wait_median_minutes'].idxmax()]

        print(f"\nBy Day of Week:")
        print(f"  Best:  {best_day['day_name']} (median wait: {best_day['wait_median_minutes']:.1f} min)")
        print(f"  Worst: {worst_day['day_name']} (median wait: {worst_day['wait_median_minutes']:.1f} min)")
        print(f"  Difference: {worst_day['wait_median_minutes'] - best_day['wait_median_minutes']:.1f} min")

    # Best month
    if monthly_df is not None and len(monthly_df) > 0:
        best_month = monthly_df.loc[monthly_df['wait_median_minutes'].idxmin()]
        worst_month = monthly_df.loc[monthly_df['wait_median_minutes'].idxmax()]

        print(f"\nBy Month:")
        print(f"  Best:  {best_month['month_name']} (median wait: {best_month['wait_median_minutes']:.1f} min)")
        print(f"  Worst: {worst_month['month_name']} (median wait: {worst_month['wait_median_minutes']:.1f} min)")
        print(f"  Difference: {worst_month['wait_median_minutes'] - best_month['wait_median_minutes']:.1f} min")

    print("\n" + "="*80)

def print_user_insights(user_df):
    """Print insights about user wait times"""
    print("\n" + "="*80)
    print("USER WAIT TIME INSIGHTS")
    print("="*80)

    if user_df is None or len(user_df) == 0:
        print("No user data available")
        return

    # Longest waiting users
    print("\nUsers with Longest Average Wait (min 100 jobs):")
    long_wait = user_df[user_df['total_jobs'] >= 100].nlargest(10, 'wait_mean_minutes')
    for idx, row in long_wait.iterrows():
        print(f"  {row['user']:20s}: {row['wait_mean_minutes']:>8.1f} min avg "
              f"({row['total_jobs']:>6,} jobs)")

    # Shortest waiting users
    print("\nUsers with Shortest Average Wait (min 100 jobs):")
    short_wait = user_df[user_df['total_jobs'] >= 100].nsmallest(10, 'wait_mean_minutes')
    for idx, row in short_wait.iterrows():
        print(f"  {row['user']:20s}: {row['wait_mean_minutes']:>8.1f} min avg "
              f"({row['total_jobs']:>6,} jobs)")

    # Users with most CPU-hours waited
    if 'total_cpu_hours_waited' in user_df.columns:
        print("\nUsers with Most CPU-Hours Waited:")
        cpu_wait = user_df.nlargest(10, 'total_cpu_hours_waited')
        for idx, row in cpu_wait.iterrows():
            print(f"  {row['user']:20s}: {row['total_cpu_hours_waited']:>12,.0f} CPU-hours waited")

    print("\n" + "="*80)

def save_results(df, user_df, group_df, hourly_df, daily_df, weekly_df, monthly_df,
                 timeseries_df, size_df):
    """Save all analysis results"""
    print("\nSaving results...")

    # Per-user stats
    if user_df is not None:
        user_df.to_csv('wait_times_per_user.csv', index=False)
        print(f"  Saved wait_times_per_user.csv ({len(user_df):,} users)")

    # Per-group stats
    if group_df is not None:
        group_df.to_csv('wait_times_per_group.csv', index=False)
        print(f"  Saved wait_times_per_group.csv ({len(group_df):,} groups)")

    # Hourly pattern
    if hourly_df is not None:
        hourly_df.to_csv('wait_times_by_hour.csv', index=False)
        print(f"  Saved wait_times_by_hour.csv (24 hours)")

    # Daily pattern
    if daily_df is not None:
        daily_df.to_csv('wait_times_by_day_of_week.csv', index=False)
        print(f"  Saved wait_times_by_day_of_week.csv (7 days)")

    # Weekly pattern
    if weekly_df is not None:
        weekly_df.to_csv('wait_times_by_week_of_month.csv', index=False)
        print(f"  Saved wait_times_by_week_of_month.csv")

    # Monthly pattern
    if monthly_df is not None:
        monthly_df.to_csv('wait_times_by_month.csv', index=False)
        print(f"  Saved wait_times_by_month.csv (12 months)")

    # Time series
    if timeseries_df is not None:
        timeseries_df.to_csv('wait_times_timeseries.csv', index=False)
        print(f"  Saved wait_times_timeseries.csv ({len(timeseries_df):,} weeks)")

    # Size analysis
    if size_df is not None:
        size_df.to_csv('wait_times_by_job_size.csv', index=False)
        print(f"  Saved wait_times_by_job_size.csv")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_queue_wait_times.py <jobs_csv>")
        print("")
        print("Analyzes queue wait times with comprehensive temporal statistics.")
        print("")
        print("Required columns:")
        print("  - submit_time: When job was submitted")
        print("  - start_time: When job started running")
        print("")
        print("Optional columns:")
        print("  - user, group: For per-user/group analysis")
        print("  - cpus: For job size analysis")
        print("")
        print("Outputs:")
        print("  - wait_times_per_user.csv - Per-user statistics")
        print("  - wait_times_per_group.csv - Per-group statistics")
        print("  - wait_times_by_hour.csv - Hourly patterns")
        print("  - wait_times_by_day_of_week.csv - Daily patterns")
        print("  - wait_times_by_week_of_month.csv - Weekly patterns")
        print("  - wait_times_by_month.csv - Monthly patterns")
        print("  - wait_times_timeseries.csv - Time series")
        print("  - wait_times_by_job_size.csv - By CPU count")
        sys.exit(1)

    jobs_file = sys.argv[1]

    # Load data
    df = load_job_data(jobs_file)

    # Overall statistics
    calculate_overall_statistics(df)

    # Per-user and per-group analysis
    user_df = analyze_per_user(df)
    group_df = analyze_per_group(df)

    # Temporal analysis
    hourly_df = analyze_by_time_of_day(df)
    daily_df = analyze_by_day_of_week(df)
    weekly_df = analyze_by_week_of_month(df)
    monthly_df = analyze_by_month(df)
    timeseries_df = analyze_over_time(df)

    # Job size analysis
    size_df = analyze_by_job_size(df)

    # Print insights
    print_temporal_insights(hourly_df, daily_df, monthly_df)
    print_user_insights(user_df)

    # Save results
    save_results(df, user_df, group_df, hourly_df, daily_df, weekly_df,
                monthly_df, timeseries_df, size_df)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nOutput files created:")
    print("  wait_times_per_user.csv          - User-level aggregates")
    print("  wait_times_per_group.csv         - Group-level aggregates")
    print("  wait_times_by_hour.csv           - 24-hour pattern")
    print("  wait_times_by_day_of_week.csv    - 7-day pattern")
    print("  wait_times_by_week_of_month.csv  - Weekly pattern")
    print("  wait_times_by_month.csv          - 12-month pattern")
    print("  wait_times_timeseries.csv        - Weekly time series")
    print("  wait_times_by_job_size.csv       - By CPU count")
    print("")
    print("Use these files to:")
    print("  - Identify best times to submit jobs")
    print("  - Understand queue congestion patterns")
    print("  - Evaluate fair share effectiveness")
    print("  - Plan job submission strategies")
    print("")
    print("="*80)

if __name__ == '__main__':
    main()
