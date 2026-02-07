#!/usr/bin/env python3
"""
Cross-User Impact Analysis

Analyzes how individual user behaviors impact other users and the system,
particularly for understanding submission abandonment triggers.

Identifies:
- High-impact jobs (large resource requests, long runtimes)
- System-wide effects on wait times, submission rates, utilization
- Temporal patterns (e.g., "User X submits large job every Tuesday")
- Submission abandonment triggers (when others stop submitting)
- Causal relationships between user behaviors

Example insights:
- "User X's Tuesday night batch jobs cause 2x wait time increase for others"
- "When User Y submits >1000 core jobs, submission rate drops 40% within 1 hour"
- "Group A's monthly jobs trigger submission abandonment in Group B"

Usage:
    python3 analyze_cross_user_impacts.py jobs_anonymized.csv [cluster_config.csv]

Outputs:
    - high_impact_jobs.csv           - Jobs with significant system impact
    - impact_events.csv              - Specific impact events with before/after
    - user_impact_patterns.csv       - Recurring patterns per user
    - submission_abandonment_triggers.csv - Events that trigger abandonment
    - temporal_impact_patterns.csv   - Day/time patterns of impacts
    - cross_group_impacts.csv        - How groups affect each other
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

    # Criteria for high-impact:
    # 1. Large CPU allocation (>10% of cluster if known, else >90th percentile)
    # 2. Long runtime (>95th percentile)
    # 3. Large memory footprint
    # 4. High CPU-hours consumed

    p90_cpus = df['cpus'].quantile(0.90)
    p95_runtime = df['runtime_seconds'].quantile(0.95)
    p90_cpu_hours = df['cpu_hours'].quantile(0.90)

    # Define thresholds
    if cluster_config:
        high_cpu_threshold = max(p90_cpus, cluster_config['total_cpus'] * 0.10)
    else:
        high_cpu_threshold = p90_cpus

    # Identify high-impact jobs
    high_impact = df[
        (df['cpus'] >= high_cpu_threshold) |
        (df['runtime_seconds'] >= p95_runtime) |
        (df['cpu_hours'] >= p90_cpu_hours)
    ].copy()

    # Calculate impact score (0-100)
    # Based on resource size, duration, and resource-time product
    high_impact['cpu_score'] = (high_impact['cpus'] / df['cpus'].max() * 100).clip(0, 100)
    high_impact['runtime_score'] = (high_impact['runtime_seconds'] / df['runtime_seconds'].max() * 100).clip(0, 100)
    high_impact['cpu_hours_score'] = (high_impact['cpu_hours'] / df['cpu_hours'].max() * 100).clip(0, 100)

    # Overall impact score (weighted average)
    high_impact['impact_score'] = (
        high_impact['cpu_score'] * 0.3 +
        high_impact['runtime_score'] * 0.3 +
        high_impact['cpu_hours_score'] * 0.4
    )

    # Add temporal info
    high_impact['day_of_week'] = high_impact['submit_time'].dt.day_name()
    high_impact['hour_of_day'] = high_impact['submit_time'].dt.hour
    high_impact['date'] = high_impact['submit_time'].dt.date

    high_impact = high_impact.sort_values('impact_score', ascending=False)

    print(f"  Identified {len(high_impact):,} high-impact jobs ({len(high_impact)/len(df)*100:.1f}% of total)")
    print(f"  Mean impact score: {high_impact['impact_score'].mean():.1f}")
    print(f"  Top job: {high_impact.iloc[0]['cpus']} CPUs, {high_impact.iloc[0]['runtime_seconds']/3600:.1f} hours")

    return high_impact

def analyze_impact_events(df, high_impact_jobs):
    """For each high-impact job, analyze system state before/after"""
    print("\nAnalyzing impact events (before/after comparison)...")

    # Time windows for analysis
    window_before = timedelta(hours=1)
    window_after = timedelta(hours=2)

    impact_events = []

    # Sample high-impact jobs to analyze (top 1000 by impact score)
    sample_size = min(1000, len(high_impact_jobs))
    sample_jobs = high_impact_jobs.nlargest(sample_size, 'impact_score')

    for idx, impact_job in sample_jobs.iterrows():
        impact_user = impact_job['user']
        impact_group = impact_job['group'] if 'group' in impact_job else None
        impact_time = impact_job['start_time']  # When job actually started

        # Define time windows
        before_start = impact_time - window_before
        before_end = impact_time
        after_start = impact_time
        after_end = impact_time + window_after

        # Get jobs from OTHER users in before/after windows
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

        # Calculate metrics before/after
        # 1. Submission rate (jobs per hour)
        submit_rate_before = len(others_before) / (window_before.total_seconds() / 3600)
        submit_rate_after = len(others_after) / (window_after.total_seconds() / 3600)
        submit_rate_change_pct = ((submit_rate_after - submit_rate_before) / submit_rate_before * 100) if submit_rate_before > 0 else 0

        # 2. Average wait time
        wait_time_before = others_before['wait_seconds'].median() / 60  # minutes
        wait_time_after = others_after['wait_seconds'].median() / 60
        wait_time_change_pct = ((wait_time_after - wait_time_before) / wait_time_before * 100) if wait_time_before > 0 else 0

        # 3. Number of unique users submitting
        users_before = others_before['user'].nunique()
        users_after = others_after['user'].nunique()
        users_change_pct = ((users_after - users_before) / users_before * 100) if users_before > 0 else 0

        # Detect submission abandonment: significant drop in submission rate or active users
        is_abandonment_trigger = (submit_rate_change_pct < -25) or (users_change_pct < -20)

        impact_events.append({
            'impact_job_id': impact_job['job_id'],
            'impact_user': impact_user,
            'impact_group': impact_group,
            'impact_time': impact_time,
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
            'is_abandonment_trigger': is_abandonment_trigger
        })

    events_df = pd.DataFrame(impact_events)

    if len(events_df) > 0:
        print(f"  Analyzed {len(events_df):,} impact events")

        abandonment_triggers = events_df[events_df['is_abandonment_trigger']]
        print(f"  Submission abandonment triggers: {len(abandonment_triggers):,} ({len(abandonment_triggers)/len(events_df)*100:.1f}%)")

        if len(abandonment_triggers) > 0:
            print(f"    Avg submission rate drop: {abandonment_triggers['submit_rate_change_pct'].mean():.1f}%")
            print(f"    Avg wait time increase: {abandonment_triggers['wait_time_change_pct'].mean():.1f}%")
    else:
        print("  No impact events with sufficient data")

    return events_df

def identify_user_impact_patterns(impact_events):
    """Identify recurring patterns for each user"""
    print("\nIdentifying recurring user impact patterns...")

    if len(impact_events) == 0:
        print("  No impact events to analyze")
        return pd.DataFrame()

    user_patterns = []

    for user in impact_events['impact_user'].unique():
        user_events = impact_events[impact_events['impact_user'] == user]

        if len(user_events) < 3:  # Need at least 3 events to identify pattern
            continue

        # Analyze temporal patterns
        day_counts = user_events['day_of_week'].value_counts()
        most_common_day = day_counts.index[0] if len(day_counts) > 0 else None
        day_concentration = (day_counts.iloc[0] / len(user_events) * 100) if len(day_counts) > 0 else 0

        # Hour patterns
        hour_mean = user_events['hour_of_day'].mean()
        hour_std = user_events['hour_of_day'].std()

        # Impact metrics
        avg_impact_score = user_events['impact_score'].mean()
        avg_cpus = user_events['impact_cpus'].mean()
        avg_submit_rate_change = user_events['submit_rate_change_pct'].mean()
        avg_wait_time_change = user_events['wait_time_change_pct'].mean()

        # Abandonment trigger rate
        abandonment_triggers = user_events[user_events['is_abandonment_trigger']]
        abandonment_trigger_rate = len(abandonment_triggers) / len(user_events) * 100

        # Frequency
        time_span = (user_events['impact_time'].max() - user_events['impact_time'].min()).days
        frequency_per_week = len(user_events) / (time_span / 7) if time_span > 0 else 0

        user_patterns.append({
            'user': user,
            'group': user_events.iloc[0]['impact_group'],
            'event_count': len(user_events),
            'frequency_per_week': frequency_per_week,
            'most_common_day': most_common_day,
            'day_concentration_pct': day_concentration,
            'avg_hour_of_day': hour_mean,
            'hour_std': hour_std,
            'avg_impact_score': avg_impact_score,
            'avg_cpus': avg_cpus,
            'avg_submit_rate_change_pct': avg_submit_rate_change,
            'avg_wait_time_change_pct': avg_wait_time_change,
            'abandonment_trigger_rate_pct': abandonment_trigger_rate,
            'is_regular_pattern': (day_concentration > 50) and (frequency_per_week > 0.5)
        })

    patterns_df = pd.DataFrame(user_patterns)

    if len(patterns_df) > 0:
        patterns_df = patterns_df.sort_values('abandonment_trigger_rate_pct', ascending=False)

        print(f"  Identified patterns for {len(patterns_df)} users")

        regular_patterns = patterns_df[patterns_df['is_regular_pattern']]
        print(f"  Users with regular patterns: {len(regular_patterns)}")

        high_impact_users = patterns_df[patterns_df['abandonment_trigger_rate_pct'] > 50]
        print(f"  Users frequently triggering abandonment: {len(high_impact_users)}")

    return patterns_df

def identify_abandonment_triggers(impact_events):
    """Identify specific characteristics of abandonment triggers"""
    print("\nAnalyzing submission abandonment triggers...")

    if len(impact_events) == 0:
        return pd.DataFrame()

    abandonment_triggers = impact_events[impact_events['is_abandonment_trigger']].copy()

    if len(abandonment_triggers) == 0:
        print("  No abandonment triggers found")
        return pd.DataFrame()

    print(f"  Analyzing {len(abandonment_triggers):,} abandonment trigger events")

    # Categorize by severity
    abandonment_triggers['severity'] = pd.cut(
        abandonment_triggers['submit_rate_change_pct'],
        bins=[-100, -50, -40, -30, 0],
        labels=['severe', 'high', 'moderate', 'mild']
    )

    # Add temporal categorization
    abandonment_triggers['time_of_day'] = pd.cut(
        abandonment_triggers['hour_of_day'],
        bins=[0, 6, 12, 18, 24],
        labels=['night', 'morning', 'afternoon', 'evening'],
        include_lowest=True
    )

    # Summary statistics
    summary_stats = abandonment_triggers.groupby('severity').agg({
        'impact_job_id': 'count',
        'impact_cpus': 'mean',
        'impact_runtime_hours': 'mean',
        'submit_rate_change_pct': 'mean',
        'wait_time_change_pct': 'mean',
        'users_change_pct': 'mean'
    }).reset_index()

    summary_stats.columns = [
        'severity', 'count', 'avg_cpus', 'avg_runtime_hours',
        'avg_submit_rate_change_pct', 'avg_wait_time_change_pct', 'avg_users_change_pct'
    ]

    print(f"  Severity distribution:")
    for _, row in summary_stats.iterrows():
        print(f"    {row['severity']}: {row['count']} events, {row['avg_submit_rate_change_pct']:.1f}% submission drop")

    return abandonment_triggers

def analyze_temporal_impact_patterns(impact_events):
    """Analyze when impacts occur (day of week, time of day)"""
    print("\nAnalyzing temporal patterns of impacts...")

    if len(impact_events) == 0:
        return pd.DataFrame()

    temporal_patterns = []

    # By day of week
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
        day_events = impact_events[impact_events['day_of_week'] == day]

        if len(day_events) > 0:
            abandonment_count = day_events[day_events['is_abandonment_trigger']].shape[0]

            temporal_patterns.append({
                'temporal_type': 'day_of_week',
                'temporal_value': day,
                'event_count': len(day_events),
                'abandonment_trigger_count': abandonment_count,
                'abandonment_rate_pct': (abandonment_count / len(day_events) * 100),
                'avg_submit_rate_change_pct': day_events['submit_rate_change_pct'].mean(),
                'avg_wait_time_change_pct': day_events['wait_time_change_pct'].mean(),
                'avg_impact_cpus': day_events['impact_cpus'].mean()
            })

    # By hour of day (group into 4-hour blocks)
    hour_blocks = [
        ('00-04', 0, 4), ('04-08', 4, 8), ('08-12', 8, 12),
        ('12-16', 12, 16), ('16-20', 16, 20), ('20-24', 20, 24)
    ]

    for block_name, start_hour, end_hour in hour_blocks:
        hour_events = impact_events[
            (impact_events['hour_of_day'] >= start_hour) &
            (impact_events['hour_of_day'] < end_hour)
        ]

        if len(hour_events) > 0:
            abandonment_count = hour_events[hour_events['is_abandonment_trigger']].shape[0]

            temporal_patterns.append({
                'temporal_type': 'hour_block',
                'temporal_value': block_name,
                'event_count': len(hour_events),
                'abandonment_trigger_count': abandonment_count,
                'abandonment_rate_pct': (abandonment_count / len(hour_events) * 100),
                'avg_submit_rate_change_pct': hour_events['submit_rate_change_pct'].mean(),
                'avg_wait_time_change_pct': hour_events['wait_time_change_pct'].mean(),
                'avg_impact_cpus': hour_events['impact_cpus'].mean()
            })

    temporal_df = pd.DataFrame(temporal_patterns)

    if len(temporal_df) > 0:
        print(f"  Analyzed {len(temporal_df)} temporal categories")

        # Find highest abandonment rate
        max_abandonment = temporal_df.loc[temporal_df['abandonment_rate_pct'].idxmax()]
        print(f"  Highest abandonment rate: {max_abandonment['temporal_value']} ({max_abandonment['abandonment_rate_pct']:.1f}%)")

    return temporal_df

def analyze_cross_group_impacts(impact_events, df):
    """Analyze how different groups impact each other"""
    print("\nAnalyzing cross-group impacts...")

    if 'group' not in df.columns or len(impact_events) == 0:
        print("  No group information available")
        return pd.DataFrame()

    cross_group_impacts = []

    for impact_group in impact_events['impact_group'].dropna().unique():
        group_events = impact_events[impact_events['impact_group'] == impact_group]

        # For this group's impact events, see how other groups were affected
        for target_group in df['group'].unique():
            if target_group == impact_group:
                continue  # Skip same group

            # Count how many times this target group submitted during impact events
            # (we'd need to track this in impact_events analysis, simplified here)

            avg_submit_rate_change = group_events['submit_rate_change_pct'].mean()
            avg_wait_time_change = group_events['wait_time_change_pct'].mean()

            abandonment_triggers = group_events[group_events['is_abandonment_trigger']]

            cross_group_impacts.append({
                'impact_group': impact_group,
                'affected_group': target_group,
                'impact_event_count': len(group_events),
                'abandonment_trigger_count': len(abandonment_triggers),
                'avg_submit_rate_change_pct': avg_submit_rate_change,
                'avg_wait_time_change_pct': avg_wait_time_change,
                'avg_impact_cpus': group_events['impact_cpus'].mean(),
                'impact_strength': abs(avg_submit_rate_change) + abs(avg_wait_time_change) / 10  # Combined metric
            })

    cross_group_df = pd.DataFrame(cross_group_impacts)

    if len(cross_group_df) > 0:
        cross_group_df = cross_group_df.sort_values('impact_strength', ascending=False)
        print(f"  Analyzed {len(cross_group_df)} group-to-group impact relationships")

        # Top impactor
        top_impact = cross_group_df.iloc[0]
        print(f"  Strongest impact: {top_impact['impact_group']} → {top_impact['affected_group']}")
        print(f"    {top_impact['impact_event_count']} events, {top_impact['avg_submit_rate_change_pct']:.1f}% submission change")

    return cross_group_df

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_cross_user_impacts.py <jobs_csv> [cluster_config_csv]")
        print("")
        print("Analyzes how individual user behaviors impact others and trigger")
        print("submission abandonment.")
        print("")
        print("Outputs:")
        print("  - high_impact_jobs.csv")
        print("  - impact_events.csv")
        print("  - user_impact_patterns.csv")
        print("  - submission_abandonment_triggers.csv")
        print("  - temporal_impact_patterns.csv")
        print("  - cross_group_impacts.csv")
        sys.exit(1)

    jobs_file = sys.argv[1]
    config_file = sys.argv[2] if len(sys.argv) > 2 else None

    print("="*70)
    print("CROSS-USER IMPACT AND SUBMISSION ABANDONMENT ANALYSIS")
    print("="*70)

    # Load data
    df = load_job_data(jobs_file)
    cluster_config = load_cluster_config(config_file) if config_file else None

    # Identify high-impact jobs
    high_impact_jobs = identify_high_impact_jobs(df, cluster_config)

    # Analyze impact events (before/after comparison)
    impact_events = analyze_impact_events(df, high_impact_jobs)

    # Identify patterns
    user_patterns = identify_user_impact_patterns(impact_events)
    abandonment_triggers = identify_abandonment_triggers(impact_events)
    temporal_patterns = analyze_temporal_impact_patterns(impact_events)
    cross_group = analyze_cross_group_impacts(impact_events, df)

    # Save outputs
    print("\n" + "="*70)
    print("SAVING RESULTS")
    print("="*70)

    high_impact_jobs.to_csv('high_impact_jobs.csv', index=False)
    print("  Saved: high_impact_jobs.csv")

    if len(impact_events) > 0:
        impact_events.to_csv('impact_events.csv', index=False)
        print("  Saved: impact_events.csv")

    if len(user_patterns) > 0:
        user_patterns.to_csv('user_impact_patterns.csv', index=False)
        print("  Saved: user_impact_patterns.csv")

    if len(abandonment_triggers) > 0:
        abandonment_triggers.to_csv('submission_abandonment_triggers.csv', index=False)
        print("  Saved: submission_abandonment_triggers.csv")

    if len(temporal_patterns) > 0:
        temporal_patterns.to_csv('temporal_impact_patterns.csv', index=False)
        print("  Saved: temporal_impact_patterns.csv")

    if len(cross_group) > 0:
        cross_group.to_csv('cross_group_impacts.csv', index=False)
        print("  Saved: cross_group_impacts.csv")

    # Summary
    print("\n" + "="*70)
    print("ANALYSIS SUMMARY")
    print("="*70)

    print(f"\nHigh-Impact Jobs: {len(high_impact_jobs):,}")
    print(f"  Top 10% CPU threshold: {high_impact_jobs['cpus'].quantile(0.90):.0f} CPUs")

    if len(impact_events) > 0:
        print(f"\nImpact Events Analyzed: {len(impact_events):,}")
        abandonment_count = impact_events[impact_events['is_abandonment_trigger']].sum()
        print(f"  Submission abandonment triggers: {abandonment_count} ({abandonment_count/len(impact_events)*100:.1f}%)")

        print(f"\nAverage Impact:")
        print(f"  Submission rate change: {impact_events['submit_rate_change_pct'].mean():.1f}%")
        print(f"  Wait time change: {impact_events['wait_time_change_pct'].mean():.1f}%")
        print(f"  Active users change: {impact_events['users_change_pct'].mean():.1f}%")

    if len(user_patterns) > 0:
        print(f"\nUser Patterns: {len(user_patterns)} users with recurring impacts")
        regular = user_patterns[user_patterns['is_regular_pattern']].shape[0]
        print(f"  Regular patterns (same day, weekly): {regular}")

        high_abandonment_users = user_patterns[user_patterns['abandonment_trigger_rate_pct'] > 50]
        if len(high_abandonment_users) > 0:
            print(f"  Users frequently triggering abandonment: {len(high_abandonment_users)}")
            print(f"    Top user: {high_abandonment_users.iloc[0]['abandonment_trigger_rate_pct']:.1f}% trigger rate")

    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)
    print("\nKey Insights:")
    print("- Review 'user_impact_patterns.csv' for recurring problematic patterns")
    print("- Check 'submission_abandonment_triggers.csv' for specific incidents")
    print("- Examine 'temporal_impact_patterns.csv' for when impacts occur")
    print("- Use 'impact_events.csv' for detailed before/after analysis")
    print("="*70)

if __name__ == '__main__':
    main()
