#!/usr/bin/env python3
"""
Cross-User Impact Analysis with Recovery Time Tracking

Enhanced version that tracks how long it takes for the system to recover
after a submission abandonment event.

Adds recovery metrics:
- Time until submission rate recovers to baseline
- Time until wait times return to normal
- Time until active user count recovers
- Whether system fully recovered within observation window

Usage:
    python3 analyze_cross_user_impacts_with_recovery.py jobs_anonymized.csv [cluster_config.csv]

Outputs:
    Same as analyze_cross_user_impacts.py, plus recovery time columns
"""

import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta
from collections import defaultdict

def load_job_data(filename):
    """Load anonymized job data"""
    print(f"Loading job data from {filename}...")

    df = pd.read_csv(filename)

    # Parse timestamps
    df['submit_time'] = pd.to_datetime(df['submit_time'])
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'])

    # Calculate durations
    df['runtime_seconds'] = (df['end_time'] - df['start_time']).dt.total_seconds()
    df['wait_seconds'] = (df['start_time'] - df['submit_time']).dt.total_seconds()

    # Filter valid jobs
    df = df[(df['runtime_seconds'] > 0) & (df['wait_seconds'] >= 0)].copy()

    # Calculate resource footprint
    df['cpu_hours'] = df['cpus'] * df['runtime_seconds'] / 3600
    df['memory_gb_hours'] = df['mem_req'] * df['runtime_seconds'] / (1024 * 3600)

    print(f"  Loaded {len(df):,} valid jobs")
    print(f"  Date range: {df['submit_time'].min()} to {df['submit_time'].max()}")

    return df

def load_cluster_config(filename):
    """Load cluster configuration if provided"""
    if filename is None:
        return None

    print(f"Loading cluster configuration from {filename}...")
    config_df = pd.read_csv(filename)

    total_cpus = config_df['cpus'].sum()
    total_memory_mb = config_df['memory_mb'].sum()

    print(f"  Total CPUs: {total_cpus:,}")
    print(f"  Total Memory: {total_memory_mb:,} MB ({total_memory_mb/1024:.1f} GB)")

    return {
        'total_cpus': total_cpus,
        'total_memory_mb': total_memory_mb
    }

def identify_high_impact_jobs(df, cluster_config):
    """Identify jobs that likely had significant system impact"""
    print("\nIdentifying high-impact jobs...")

    p90_cpus = df['cpus'].quantile(0.90)
    p95_runtime = df['runtime_seconds'].quantile(0.95)
    p90_cpu_hours = df['cpu_hours'].quantile(0.90)

    if cluster_config:
        high_cpu_threshold = max(p90_cpus, cluster_config['total_cpus'] * 0.10)
    else:
        high_cpu_threshold = p90_cpus

    high_impact = df[
        (df['cpus'] >= high_cpu_threshold) |
        (df['runtime_seconds'] >= p95_runtime) |
        (df['cpu_hours'] >= p90_cpu_hours)
    ].copy()

    high_impact['cpu_score'] = (high_impact['cpus'] / df['cpus'].max() * 100).clip(0, 100)
    high_impact['runtime_score'] = (high_impact['runtime_seconds'] / df['runtime_seconds'].max() * 100).clip(0, 100)
    high_impact['cpu_hours_score'] = (high_impact['cpu_hours'] / df['cpu_hours'].max() * 100).clip(0, 100)

    high_impact['impact_score'] = (
        high_impact['cpu_score'] * 0.3 +
        high_impact['runtime_score'] * 0.3 +
        high_impact['cpu_hours_score'] * 0.4
    )

    high_impact['day_of_week'] = high_impact['submit_time'].dt.day_name()
    high_impact['hour_of_day'] = high_impact['submit_time'].dt.hour
    high_impact['date'] = high_impact['submit_time'].dt.date

    high_impact = high_impact.sort_values('impact_score', ascending=False)

    print(f"  Identified {len(high_impact):,} high-impact jobs ({len(high_impact)/len(df)*100:.1f}% of total)")
    print(f"  Mean impact score: {high_impact['impact_score'].mean():.1f}")
    print(f"  Top job: {high_impact.iloc[0]['cpus']} CPUs, {high_impact.iloc[0]['runtime_seconds']/3600:.1f} hours")

    return high_impact

def calculate_recovery_time(df, impact_user, impact_time, impact_end_time, baseline_submit_rate, baseline_users, baseline_wait_time, max_recovery_hours=12):
    """
    Track system metrics over time to determine recovery time

    Returns recovery times for:
    - Submission rate
    - Active user count
    - Wait times
    """

    # Recovery thresholds (within 20% of baseline = recovered)
    submit_rate_threshold = baseline_submit_rate * 0.80
    users_threshold = baseline_users * 0.80
    wait_time_threshold = baseline_wait_time * 1.20  # Within 120% (allow 20% higher)

    # Sample system state every 30 minutes after impact
    sampling_interval = timedelta(minutes=30)
    max_recovery_time = timedelta(hours=max_recovery_hours)

    recovery_times = {
        'submit_rate_recovery_hours': None,
        'users_recovery_hours': None,
        'wait_time_recovery_hours': None,
        'full_recovery_hours': None,
        'submit_rate_recovered': False,
        'users_recovered': False,
        'wait_time_recovered': False,
        'fully_recovered': False
    }

    current_time = impact_time
    end_time = min(impact_time + max_recovery_time, df['submit_time'].max())

    submit_rate_recovered = False
    users_recovered = False
    wait_time_recovered = False

    while current_time < end_time:
        window_start = current_time
        window_end = current_time + timedelta(hours=1)  # 1 hour window

        # Get other users' submissions in this window
        others_window = df[
            (df['user'] != impact_user) &
            (df['submit_time'] >= window_start) &
            (df['submit_time'] < window_end)
        ]

        if len(others_window) >= 5:  # Need minimum data
            # Calculate metrics
            submit_rate = len(others_window) / 1.0  # jobs per hour
            active_users = others_window['user'].nunique()
            wait_time = others_window['wait_seconds'].median() / 60  # minutes

            elapsed_hours = (current_time - impact_time).total_seconds() / 3600

            # Check if submission rate recovered
            if not submit_rate_recovered and submit_rate >= submit_rate_threshold:
                recovery_times['submit_rate_recovery_hours'] = elapsed_hours
                recovery_times['submit_rate_recovered'] = True
                submit_rate_recovered = True

            # Check if user count recovered
            if not users_recovered and active_users >= users_threshold:
                recovery_times['users_recovery_hours'] = elapsed_hours
                recovery_times['users_recovered'] = True
                users_recovered = True

            # Check if wait time recovered (not too high)
            if not wait_time_recovered and wait_time <= wait_time_threshold:
                recovery_times['wait_time_recovery_hours'] = elapsed_hours
                recovery_times['wait_time_recovered'] = True
                wait_time_recovered = True

            # Check if full recovery
            if submit_rate_recovered and users_recovered and wait_time_recovered:
                if recovery_times['full_recovery_hours'] is None:
                    recovery_times['full_recovery_hours'] = max(
                        recovery_times['submit_rate_recovery_hours'],
                        recovery_times['users_recovery_hours'],
                        recovery_times['wait_time_recovery_hours']
                    )
                    recovery_times['fully_recovered'] = True
                break  # Found full recovery

        current_time += sampling_interval

    return recovery_times

def analyze_impact_events_with_recovery(df, high_impact_jobs):
    """For each high-impact job, analyze system state before/after and track recovery"""
    print("\nAnalyzing impact events with recovery tracking...")

    window_before = timedelta(hours=1)
    window_after = timedelta(hours=2)

    impact_events = []

    # Sample high-impact jobs to analyze
    sample_size = min(100, len(high_impact_jobs))  # Reduced for recovery tracking (more compute)
    sample_jobs = high_impact_jobs.nlargest(sample_size, 'impact_score')

    print(f"  Analyzing top {sample_size} impact events for recovery patterns...")

    for idx, impact_job in sample_jobs.iterrows():
        impact_user = impact_job['user']
        impact_group = impact_job['group'] if 'group' in impact_job else None
        impact_time = impact_job['start_time']
        impact_end_time = impact_job['end_time']

        # Define time windows
        before_start = impact_time - window_before
        before_end = impact_time
        after_start = impact_time
        after_end = impact_time + window_after

        # Get jobs from OTHER users
        others_before = df[
            (df['user'] != impact_user) &
            (df['submit_time'] >= before_start) &
            (df['submit_time'] < before_end)
        ]

        others_after = df[
            (df['user'] != impact_user) &
            (df['submit_time'] >= after_start) &
            (df['submit_time'] < after_end)
        ]

        # Skip if not enough data
        if len(others_before) < 5 or len(others_after) < 5:
            continue

        # Calculate baseline metrics (before impact)
        submit_rate_before = len(others_before) / (window_before.total_seconds() / 3600)
        wait_time_before = others_before['wait_seconds'].median() / 60
        users_before = others_before['user'].nunique()

        # Calculate immediate after metrics
        submit_rate_after = len(others_after) / (window_after.total_seconds() / 3600)
        submit_rate_change_pct = ((submit_rate_after - submit_rate_before) / submit_rate_before * 100) if submit_rate_before > 0 else 0

        wait_time_after = others_after['wait_seconds'].median() / 60
        wait_time_change_pct = ((wait_time_after - wait_time_before) / wait_time_before * 100) if wait_time_before > 0 else 0

        users_after = others_after['user'].nunique()
        users_change_pct = ((users_after - users_before) / users_before * 100) if users_before > 0 else 0

        # Detect abandonment
        is_abandonment_trigger = (submit_rate_change_pct < -25) or (users_change_pct < -20)

        # Track recovery time (only for abandonment triggers to save compute)
        recovery_data = {
            'submit_rate_recovery_hours': None,
            'users_recovery_hours': None,
            'wait_time_recovery_hours': None,
            'full_recovery_hours': None,
            'submit_rate_recovered': False,
            'users_recovered': False,
            'wait_time_recovered': False,
            'fully_recovered': False
        }

        if is_abandonment_trigger:
            recovery_data = calculate_recovery_time(
                df, impact_user, impact_time, impact_end_time,
                submit_rate_before, users_before, wait_time_before
            )

        impact_events.append({
            'impact_job_id': impact_job['job_id'],
            'impact_user': impact_user,
            'impact_group': impact_group,
            'impact_time': impact_time,
            'impact_end_time': impact_end_time,
            'impact_cpus': impact_job['cpus'],
            'impact_runtime_hours': impact_job['runtime_seconds'] / 3600,
            'impact_score': impact_job['impact_score'],
            'day_of_week': impact_job['day_of_week'],
            'hour_of_day': impact_job['hour_of_day'],
            'submit_rate_before': submit_rate_before,
            'submit_rate_after': submit_rate_after,
            'submit_rate_change_pct': submit_rate_change_pct,
            'wait_time_before_min': wait_time_before,
            'wait_time_after_min': wait_time_after,
            'wait_time_change_pct': wait_time_change_pct,
            'active_users_before': users_before,
            'active_users_after': users_after,
            'users_change_pct': users_change_pct,
            'is_abandonment_trigger': is_abandonment_trigger,
            **recovery_data  # Add all recovery metrics
        })

    events_df = pd.DataFrame(impact_events)

    if len(events_df) > 0:
        print(f"  Analyzed {len(events_df):,} impact events")

        abandonment_triggers = events_df[events_df['is_abandonment_trigger']]
        print(f"  Submission abandonment triggers: {len(abandonment_triggers):,} ({len(abandonment_triggers)/len(events_df)*100:.1f}%)")

        if len(abandonment_triggers) > 0:
            print(f"\n  Recovery Statistics:")

            recovered_submit = abandonment_triggers['submit_rate_recovered'].sum()
            print(f"    Submission rate recovered: {recovered_submit}/{len(abandonment_triggers)} ({recovered_submit/len(abandonment_triggers)*100:.1f}%)")
            if recovered_submit > 0:
                avg_recovery = abandonment_triggers[abandonment_triggers['submit_rate_recovered']]['submit_rate_recovery_hours'].mean()
                print(f"      Average recovery time: {avg_recovery:.1f} hours")

            recovered_users = abandonment_triggers['users_recovered'].sum()
            print(f"    User count recovered: {recovered_users}/{len(abandonment_triggers)} ({recovered_users/len(abandonment_triggers)*100:.1f}%)")
            if recovered_users > 0:
                avg_recovery = abandonment_triggers[abandonment_triggers['users_recovered']]['users_recovery_hours'].mean()
                print(f"      Average recovery time: {avg_recovery:.1f} hours")

            fully_recovered = abandonment_triggers['fully_recovered'].sum()
            print(f"    Full recovery: {fully_recovered}/{len(abandonment_triggers)} ({fully_recovered/len(abandonment_triggers)*100:.1f}%)")
            if fully_recovered > 0:
                avg_recovery = abandonment_triggers[abandonment_triggers['fully_recovered']]['full_recovery_hours'].mean()
                print(f"      Average full recovery time: {avg_recovery:.1f} hours")

    else:
        print("  No impact events with sufficient data")

    return events_df

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_cross_user_impacts_with_recovery.py <jobs_csv> [cluster_config_csv]")
        print("")
        print("Analyzes cross-user impacts with recovery time tracking.")
        sys.exit(1)

    jobs_file = sys.argv[1]
    config_file = sys.argv[2] if len(sys.argv) > 2 else None

    print("="*70)
    print("CROSS-USER IMPACT ANALYSIS WITH RECOVERY TRACKING")
    print("="*70)

    # Load data
    df = load_job_data(jobs_file)
    cluster_config = load_cluster_config(config_file) if config_file else None

    # Identify high-impact jobs
    high_impact_jobs = identify_high_impact_jobs(df, cluster_config)

    # Analyze with recovery tracking
    impact_events = analyze_impact_events_with_recovery(df, high_impact_jobs)

    # Save results
    print("\n" + "="*70)
    print("SAVING RESULTS")
    print("="*70)

    if len(impact_events) > 0:
        impact_events.to_csv('impact_events_with_recovery.csv', index=False)
        print("  Saved: impact_events_with_recovery.csv")

        # Summary statistics
        print("\n" + "="*70)
        print("RECOVERY TIME SUMMARY")
        print("="*70)

        abandonment = impact_events[impact_events['is_abandonment_trigger']]

        if len(abandonment) > 0:
            print(f"\nTotal abandonment events: {len(abandonment)}")
            print(f"\nRecovery rates:")
            print(f"  Submission rate: {abandonment['submit_rate_recovered'].sum()}/{len(abandonment)} ({abandonment['submit_rate_recovered'].mean()*100:.1f}%)")
            print(f"  User count: {abandonment['users_recovered'].sum()}/{len(abandonment)} ({abandonment['users_recovered'].mean()*100:.1f}%)")
            print(f"  Wait times: {abandonment['wait_time_recovered'].sum()}/{len(abandonment)} ({abandonment['wait_time_recovered'].mean()*100:.1f}%)")
            print(f"  Full recovery: {abandonment['fully_recovered'].sum()}/{len(abandonment)} ({abandonment['fully_recovered'].mean()*100:.1f}%)")

            # Average recovery times (for those that recovered)
            print(f"\nAverage recovery times (hours):")
            recovered_submit = abandonment[abandonment['submit_rate_recovered']]
            if len(recovered_submit) > 0:
                print(f"  Submission rate: {recovered_submit['submit_rate_recovery_hours'].mean():.2f}")

            recovered_users = abandonment[abandonment['users_recovered']]
            if len(recovered_users) > 0:
                print(f"  User count: {recovered_users['users_recovery_hours'].mean():.2f}")

            recovered_wait = abandonment[abandonment['wait_time_recovered']]
            if len(recovered_wait) > 0:
                print(f"  Wait times: {recovered_wait['wait_time_recovery_hours'].mean():.2f}")

            fully_recovered = abandonment[abandonment['fully_recovered']]
            if len(fully_recovered) > 0:
                print(f"  Full recovery: {fully_recovered['full_recovery_hours'].mean():.2f}")
    else:
        print("  No impact events to save")

    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)

if __name__ == '__main__':
    main()
