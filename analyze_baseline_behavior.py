#!/usr/bin/env python3
"""
Baseline Submission Behavior Analysis

Establishes normal submission patterns to:
1. Better detect anomalies (deviations from baseline)
2. Accurately measure recovery (return to baseline)
3. Understand typical user/group behavior

Analyzes:
- System-wide baseline: submission rates by hour/day/week
- Per-user baseline: typical submission patterns
- Per-group baseline: group-level norms
- Temporal variations: how baseline changes over time
- Burstiness metrics: variability in submission patterns

Outputs can be used by impact analysis for better anomaly detection.

Usage:
    python3 analyze_baseline_behavior.py jobs_anonymized.csv

Outputs:
    - baseline_system_hourly.csv      - System baseline by hour of day
    - baseline_system_daily.csv       - System baseline by day of week
    - baseline_per_user.csv           - Each user's typical pattern
    - baseline_per_group.csv          - Each group's typical pattern
    - baseline_temporal_trends.csv    - How baseline changes over time
    - baseline_statistics.csv         - Overall baseline metrics
"""

import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta
from collections import defaultdict

def load_job_data(filename):
    """Load job data"""
    print(f"Loading job data from {filename}...")

    df = pd.read_csv(filename)
    df['submit_time'] = pd.to_datetime(df['submit_time'])
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'])

    df['runtime_seconds'] = (df['end_time'] - df['start_time']).dt.total_seconds()
    df['wait_seconds'] = (df['start_time'] - df['submit_time']).dt.total_seconds()

    df = df[(df['runtime_seconds'] > 0) & (df['wait_seconds'] >= 0)].copy()

    print(f"  Loaded {len(df):,} valid jobs")
    print(f"  Date range: {df['submit_time'].min()} to {df['submit_time'].max()}")

    return df

def analyze_system_baseline_hourly(df):
    """Analyze system-wide baseline by hour of day"""
    print("\nAnalyzing system baseline by hour of day...")

    df['hour'] = df['submit_time'].dt.hour

    hourly_stats = []

    for hour in range(24):
        hour_data = df[df['hour'] == hour]

        if len(hour_data) > 0:
            # Group by day to get daily submission counts for this hour
            hour_data['date'] = hour_data['submit_time'].dt.date
            daily_counts = hour_data.groupby('date').size()

            hourly_stats.append({
                'hour': hour,
                'total_submissions': len(hour_data),
                'mean_submissions_per_day': daily_counts.mean(),
                'median_submissions_per_day': daily_counts.median(),
                'std_submissions_per_day': daily_counts.std(),
                'p25_submissions': daily_counts.quantile(0.25),
                'p75_submissions': daily_counts.quantile(0.75),
                'mean_cpus': hour_data['cpus'].mean(),
                'median_cpus': hour_data['cpus'].median(),
                'unique_users_avg': hour_data.groupby('date')['user'].nunique().mean() if 'user' in hour_data.columns else 0,
                'mean_wait_minutes': hour_data['wait_seconds'].mean() / 60
            })

    hourly_df = pd.DataFrame(hourly_stats)
    print(f"  Generated baseline for 24 hours")

    return hourly_df

def analyze_system_baseline_daily(df):
    """Analyze system-wide baseline by day of week"""
    print("\nAnalyzing system baseline by day of week...")

    df['dayofweek'] = df['submit_time'].dt.dayofweek
    df['week'] = df['submit_time'].dt.to_period('W')

    daily_stats = []

    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    for day_num in range(7):
        day_data = df[df['dayofweek'] == day_num]

        if len(day_data) > 0:
            # Group by week to get weekly submission counts for this day
            weekly_counts = day_data.groupby('week').size()

            daily_stats.append({
                'day_of_week': day_names[day_num],
                'day_num': day_num,
                'total_submissions': len(day_data),
                'mean_submissions_per_week': weekly_counts.mean(),
                'median_submissions_per_week': weekly_counts.median(),
                'std_submissions_per_week': weekly_counts.std(),
                'p25_submissions': weekly_counts.quantile(0.25),
                'p75_submissions': weekly_counts.quantile(0.75),
                'mean_cpus': day_data['cpus'].mean(),
                'median_cpus': day_data['cpus'].median(),
                'unique_users_avg': day_data.groupby('week')['user'].nunique().mean() if 'user' in day_data.columns else 0,
                'mean_wait_minutes': day_data['wait_seconds'].mean() / 60
            })

    daily_df = pd.DataFrame(daily_stats)
    print(f"  Generated baseline for 7 days")

    return daily_df

def analyze_user_baselines(df):
    """Analyze per-user baseline patterns"""
    print("\nAnalyzing per-user baseline patterns...")

    if 'user' not in df.columns:
        print("  No user column found")
        return pd.DataFrame()

    user_stats = []

    for user in df['user'].unique():
        user_data = df[df['user'] == user]

        if len(user_data) >= 10:  # Need minimum data for baseline
            # Calculate time span
            time_span_days = (user_data['submit_time'].max() - user_data['submit_time'].min()).days
            if time_span_days == 0:
                time_span_days = 1

            # Submission frequency
            submissions_per_day = len(user_data) / time_span_days

            # Inter-arrival times
            user_data_sorted = user_data.sort_values('submit_time')
            inter_arrival = user_data_sorted['submit_time'].diff().dt.total_seconds() / 3600  # hours
            inter_arrival = inter_arrival[inter_arrival.notna()]

            # Resource usage patterns
            cpus_mean = user_data['cpus'].mean()
            cpus_std = user_data['cpus'].std()
            cpus_cv = cpus_std / cpus_mean if cpus_mean > 0 else 0  # Coefficient of variation

            # Temporal patterns
            hour_dist = user_data['submit_time'].dt.hour.value_counts()
            most_active_hour = hour_dist.index[0] if len(hour_dist) > 0 else None
            hour_concentration = (hour_dist.iloc[0] / len(user_data) * 100) if len(hour_dist) > 0 else 0

            day_dist = user_data['submit_time'].dt.dayofweek.value_counts()
            most_active_day = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][day_dist.index[0]] if len(day_dist) > 0 else None
            day_concentration = (day_dist.iloc[0] / len(user_data) * 100) if len(day_dist) > 0 else 0

            # Burstiness (Coefficient of Variation of inter-arrival times)
            burstiness = (inter_arrival.std() - inter_arrival.mean()) / (inter_arrival.std() + inter_arrival.mean()) if len(inter_arrival) > 0 and (inter_arrival.std() + inter_arrival.mean()) > 0 else 0

            user_stats.append({
                'user': user,
                'group': user_data.iloc[0]['group'] if 'group' in user_data.columns else None,
                'total_jobs': len(user_data),
                'submissions_per_day': submissions_per_day,
                'mean_inter_arrival_hours': inter_arrival.mean() if len(inter_arrival) > 0 else None,
                'median_inter_arrival_hours': inter_arrival.median() if len(inter_arrival) > 0 else None,
                'burstiness_index': burstiness,
                'mean_cpus': cpus_mean,
                'std_cpus': cpus_std,
                'cv_cpus': cpus_cv,
                'most_active_hour': most_active_hour,
                'hour_concentration_pct': hour_concentration,
                'most_active_day': most_active_day,
                'day_concentration_pct': day_concentration,
                'mean_wait_minutes': user_data['wait_seconds'].mean() / 60,
                'median_wait_minutes': user_data['wait_seconds'].median() / 60,
                'is_regular_pattern': (day_concentration > 30) or (hour_concentration > 20)
            })

    user_df = pd.DataFrame(user_stats)
    if len(user_df) > 0:
        user_df = user_df.sort_values('submissions_per_day', ascending=False)

    print(f"  Analyzed {len(user_df)} users with sufficient data (≥10 jobs)")

    return user_df

def analyze_group_baselines(df):
    """Analyze per-group baseline patterns"""
    print("\nAnalyzing per-group baseline patterns...")

    if 'group' not in df.columns:
        print("  No group column found")
        return pd.DataFrame()

    group_stats = []

    for group in df['group'].unique():
        group_data = df[df['group'] == group]

        time_span_days = (group_data['submit_time'].max() - group_data['submit_time'].min()).days
        if time_span_days == 0:
            time_span_days = 1

        submissions_per_day = len(group_data) / time_span_days

        # Inter-arrival times (group level)
        group_data_sorted = group_data.sort_values('submit_time')
        inter_arrival = group_data_sorted['submit_time'].diff().dt.total_seconds() / 3600
        inter_arrival = inter_arrival[inter_arrival.notna()]

        # Burstiness
        burstiness = (inter_arrival.std() - inter_arrival.mean()) / (inter_arrival.std() + inter_arrival.mean()) if len(inter_arrival) > 0 and (inter_arrival.std() + inter_arrival.mean()) > 0 else 0

        group_stats.append({
            'group': group,
            'total_jobs': len(group_data),
            'unique_users': group_data['user'].nunique() if 'user' in group_data.columns else 0,
            'submissions_per_day': submissions_per_day,
            'mean_inter_arrival_hours': inter_arrival.mean() if len(inter_arrival) > 0 else None,
            'median_inter_arrival_hours': inter_arrival.median() if len(inter_arrival) > 0 else None,
            'burstiness_index': burstiness,
            'mean_cpus': group_data['cpus'].mean(),
            'median_cpus': group_data['cpus'].median(),
            'p90_cpus': group_data['cpus'].quantile(0.90),
            'mean_wait_minutes': group_data['wait_seconds'].mean() / 60,
            'median_wait_minutes': group_data['wait_seconds'].median() / 60
        })

    group_df = pd.DataFrame(group_stats)
    if len(group_df) > 0:
        group_df = group_df.sort_values('submissions_per_day', ascending=False)

    print(f"  Analyzed {len(group_df)} groups")

    return group_df

def analyze_temporal_trends(df):
    """Analyze how baseline changes over time"""
    print("\nAnalyzing temporal trends in baseline...")

    # Group by month
    df['month'] = df['submit_time'].dt.to_period('M')

    monthly_stats = []

    for month in df['month'].unique():
        month_data = df[df['month'] == month]

        # Daily submission rate for this month
        month_data['date'] = month_data['submit_time'].dt.date
        daily_counts = month_data.groupby('date').size()

        monthly_stats.append({
            'month': str(month),
            'total_jobs': len(month_data),
            'mean_jobs_per_day': daily_counts.mean(),
            'median_jobs_per_day': daily_counts.median(),
            'std_jobs_per_day': daily_counts.std(),
            'mean_cpus': month_data['cpus'].mean(),
            'unique_users': month_data['user'].nunique() if 'user' in month_data.columns else 0,
            'mean_wait_minutes': month_data['wait_seconds'].mean() / 60
        })

    monthly_df = pd.DataFrame(monthly_stats)
    print(f"  Generated temporal trends for {len(monthly_df)} months")

    return monthly_df

def generate_baseline_statistics(df, hourly_baseline, daily_baseline, user_baseline, group_baseline):
    """Generate overall baseline statistics summary"""
    print("\nGenerating baseline statistics summary...")

    stats = []

    # Overall system baseline
    time_span_days = (df['submit_time'].max() - df['submit_time'].min()).days
    stats.append({
        'metric': 'system_jobs_per_day',
        'value': len(df) / time_span_days if time_span_days > 0 else 0,
        'unit': 'jobs/day',
        'category': 'system'
    })

    stats.append({
        'metric': 'system_jobs_per_hour',
        'value': len(df) / (time_span_days * 24) if time_span_days > 0 else 0,
        'unit': 'jobs/hour',
        'category': 'system'
    })

    if len(hourly_baseline) > 0:
        stats.append({
            'metric': 'peak_hour',
            'value': hourly_baseline.loc[hourly_baseline['mean_submissions_per_day'].idxmax(), 'hour'],
            'unit': 'hour',
            'category': 'system'
        })

        stats.append({
            'metric': 'off_peak_hour',
            'value': hourly_baseline.loc[hourly_baseline['mean_submissions_per_day'].idxmin(), 'hour'],
            'unit': 'hour',
            'category': 'system'
        })

    if len(daily_baseline) > 0:
        stats.append({
            'metric': 'busiest_day',
            'value': daily_baseline.loc[daily_baseline['mean_submissions_per_week'].idxmax(), 'day_of_week'],
            'unit': 'day',
            'category': 'system'
        })

        stats.append({
            'metric': 'quietest_day',
            'value': daily_baseline.loc[daily_baseline['mean_submissions_per_week'].idxmin(), 'day_of_week'],
            'unit': 'day',
            'category': 'system'
        })

    # User baseline statistics
    if len(user_baseline) > 0:
        stats.append({
            'metric': 'users_with_regular_patterns',
            'value': user_baseline['is_regular_pattern'].sum(),
            'unit': 'users',
            'category': 'users'
        })

        stats.append({
            'metric': 'mean_user_burstiness',
            'value': user_baseline['burstiness_index'].mean(),
            'unit': 'index',
            'category': 'users'
        })

        stats.append({
            'metric': 'users_analyzed',
            'value': len(user_baseline),
            'unit': 'users',
            'category': 'users'
        })

    # Group baseline statistics
    if len(group_baseline) > 0:
        stats.append({
            'metric': 'groups_analyzed',
            'value': len(group_baseline),
            'unit': 'groups',
            'category': 'groups'
        })

        stats.append({
            'metric': 'mean_group_burstiness',
            'value': group_baseline['burstiness_index'].mean(),
            'unit': 'index',
            'category': 'groups'
        })

    stats_df = pd.DataFrame(stats)
    print(f"  Generated {len(stats_df)} baseline statistics")

    return stats_df

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_baseline_behavior.py <jobs_csv>")
        print("")
        print("Establishes baseline submission behavior patterns.")
        sys.exit(1)

    jobs_file = sys.argv[1]

    print("="*70)
    print("BASELINE SUBMISSION BEHAVIOR ANALYSIS")
    print("="*70)

    # Load data
    df = load_job_data(jobs_file)

    # Analyze baselines
    hourly_baseline = analyze_system_baseline_hourly(df)
    daily_baseline = analyze_system_baseline_daily(df)
    user_baseline = analyze_user_baselines(df)
    group_baseline = analyze_group_baselines(df)
    temporal_trends = analyze_temporal_trends(df)
    baseline_stats = generate_baseline_statistics(df, hourly_baseline, daily_baseline, user_baseline, group_baseline)

    # Save outputs
    print("\n" + "="*70)
    print("SAVING RESULTS")
    print("="*70)

    hourly_baseline.to_csv('baseline_system_hourly.csv', index=False)
    print("  Saved: baseline_system_hourly.csv")

    daily_baseline.to_csv('baseline_system_daily.csv', index=False)
    print("  Saved: baseline_system_daily.csv")

    if len(user_baseline) > 0:
        user_baseline.to_csv('baseline_per_user.csv', index=False)
        print("  Saved: baseline_per_user.csv")

    if len(group_baseline) > 0:
        group_baseline.to_csv('baseline_per_group.csv', index=False)
        print("  Saved: baseline_per_group.csv")

    temporal_trends.to_csv('baseline_temporal_trends.csv', index=False)
    print("  Saved: baseline_temporal_trends.csv")

    baseline_stats.to_csv('baseline_statistics.csv', index=False)
    print("  Saved: baseline_statistics.csv")

    # Summary
    print("\n" + "="*70)
    print("BASELINE SUMMARY")
    print("="*70)
    print(baseline_stats.to_string(index=False))

    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)
    print("\nThese baselines can be used to:")
    print("  1. Detect anomalies (deviations from normal)")
    print("  2. Measure recovery (return to baseline)")
    print("  3. Identify unusual user behavior")
    print("  4. Set expectations for system performance")
    print("="*70)

if __name__ == '__main__':
    main()
