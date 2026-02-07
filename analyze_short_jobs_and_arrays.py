#!/usr/bin/env python3
"""
Short Jobs and Job Array Analysis

Analyzes very short runtime jobs (potential workflow steps) and job arrays
to understand their behavior patterns and impact on scheduler overhead.

Identifies:
- Very short jobs (< 1min, < 5min thresholds)
- Job array patterns (array IDs, similar submissions)
- Workflow sequences (rapid successive submissions)
- Per-user and per-group patterns
- Temporal distributions
- Scheduler overhead impact
- System efficiency implications

Usage:
    python3 analyze_short_jobs_and_arrays.py jobs_anonymized.csv

Outputs:
    - short_jobs_summary.csv          - Overall short job statistics
    - short_jobs_by_user.csv          - Per-user short job patterns
    - short_jobs_by_group.csv         - Per-group short job patterns
    - short_jobs_temporal.csv         - Hour/day patterns
    - job_arrays_detected.csv         - Detected job array patterns
    - workflow_sequences.csv          - Potential workflow sequences
    - scheduler_overhead_analysis.csv - Overhead impact estimates
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

    # Calculate runtime in seconds
    df['runtime_seconds'] = (df['end_time'] - df['start_time']).dt.total_seconds()

    # Calculate wait time
    df['wait_seconds'] = (df['start_time'] - df['submit_time']).dt.total_seconds()

    # Filter to completed jobs with valid runtime
    df = df[df['runtime_seconds'] > 0].copy()

    print(f"  Loaded {len(df):,} completed jobs")
    print(f"  Runtime range: {df['runtime_seconds'].min():.1f}s to {df['runtime_seconds'].max():.1f}s")

    return df

def analyze_short_jobs_summary(df):
    """Analyze overall short job statistics"""
    print("\nAnalyzing short job statistics...")

    # Define thresholds (in seconds)
    thresholds = {
        'ultra_short_30s': 30,
        'very_short_1min': 60,
        'short_5min': 300,
        'short_15min': 900,
        'short_1hour': 3600
    }

    results = []

    for label, threshold in thresholds.items():
        short_jobs = df[df['runtime_seconds'] <= threshold]
        count = len(short_jobs)
        pct_jobs = (count / len(df)) * 100

        if count > 0:
            # Calculate resources consumed
            total_cpu_seconds = (short_jobs['cpus'] * short_jobs['runtime_seconds']).sum()
            total_cpu_hours = total_cpu_seconds / 3600

            # Calculate percentage of total CPU hours
            all_cpu_hours = (df['cpus'] * df['runtime_seconds']).sum() / 3600
            pct_cpu_hours = (total_cpu_hours / all_cpu_hours) * 100

            # Average wait time
            avg_wait_minutes = short_jobs['wait_seconds'].mean() / 60

            # Overhead estimate (scheduler processing time per job)
            # Assume ~1-5 seconds overhead per job for scheduling
            estimated_overhead_hours = (count * 3) / 3600  # 3 sec avg per job
            overhead_ratio = (estimated_overhead_hours / total_cpu_hours) * 100 if total_cpu_hours > 0 else 0

            results.append({
                'threshold': label,
                'threshold_seconds': threshold,
                'job_count': count,
                'pct_of_jobs': pct_jobs,
                'total_cpu_hours': total_cpu_hours,
                'pct_of_cpu_hours': pct_cpu_hours,
                'avg_runtime_seconds': short_jobs['runtime_seconds'].mean(),
                'median_runtime_seconds': short_jobs['runtime_seconds'].median(),
                'avg_wait_minutes': avg_wait_minutes,
                'estimated_scheduler_overhead_hours': estimated_overhead_hours,
                'overhead_ratio_pct': overhead_ratio,
                'unique_users': short_jobs['user'].nunique() if 'user' in short_jobs.columns else 0,
                'unique_groups': short_jobs['group'].nunique() if 'group' in short_jobs.columns else 0
            })

    summary_df = pd.DataFrame(results)
    print(f"  Analyzed {len(thresholds)} threshold categories")

    return summary_df

def analyze_short_jobs_by_user(df):
    """Analyze short job patterns per user"""
    print("\nAnalyzing short jobs by user...")

    if 'user' not in df.columns:
        print("  Warning: No user column found")
        return pd.DataFrame()

    # Focus on jobs under 5 minutes
    short_threshold = 300  # 5 minutes
    short_jobs = df[df['runtime_seconds'] <= short_threshold].copy()

    user_stats = []

    for user in df['user'].unique():
        user_jobs = df[df['user'] == user]
        user_short = short_jobs[short_jobs['user'] == user]

        if len(user_short) > 0:
            total_jobs = len(user_jobs)
            short_count = len(user_short)
            pct_short = (short_count / total_jobs) * 100

            # CPU hours
            short_cpu_hours = (user_short['cpus'] * user_short['runtime_seconds']).sum() / 3600
            total_cpu_hours = (user_jobs['cpus'] * user_jobs['runtime_seconds']).sum() / 3600
            pct_cpu_hours = (short_cpu_hours / total_cpu_hours) * 100 if total_cpu_hours > 0 else 0

            user_stats.append({
                'user': user,
                'total_jobs': total_jobs,
                'short_jobs': short_count,
                'pct_short_jobs': pct_short,
                'short_cpu_hours': short_cpu_hours,
                'total_cpu_hours': total_cpu_hours,
                'pct_cpu_hours_short': pct_cpu_hours,
                'avg_short_runtime_seconds': user_short['runtime_seconds'].mean(),
                'median_short_runtime_seconds': user_short['runtime_seconds'].median(),
                'avg_cpus_short': user_short['cpus'].mean()
            })

    user_df = pd.DataFrame(user_stats)

    # Sort by number of short jobs
    user_df = user_df.sort_values('short_jobs', ascending=False)

    print(f"  Analyzed {len(user_df)} users with short jobs")

    return user_df

def analyze_short_jobs_by_group(df):
    """Analyze short job patterns per group"""
    print("\nAnalyzing short jobs by group...")

    if 'group' not in df.columns:
        print("  Warning: No group column found")
        return pd.DataFrame()

    # Focus on jobs under 5 minutes
    short_threshold = 300  # 5 minutes
    short_jobs = df[df['runtime_seconds'] <= short_threshold].copy()

    group_stats = []

    for group in df['group'].unique():
        group_jobs = df[df['group'] == group]
        group_short = short_jobs[short_jobs['group'] == group]

        if len(group_short) > 0:
            total_jobs = len(group_jobs)
            short_count = len(group_short)
            pct_short = (short_count / total_jobs) * 100

            # CPU hours
            short_cpu_hours = (group_short['cpus'] * group_short['runtime_seconds']).sum() / 3600
            total_cpu_hours = (group_jobs['cpus'] * group_jobs['runtime_seconds']).sum() / 3600
            pct_cpu_hours = (short_cpu_hours / total_cpu_hours) * 100 if total_cpu_hours > 0 else 0

            group_stats.append({
                'group': group,
                'total_jobs': total_jobs,
                'short_jobs': short_count,
                'pct_short_jobs': pct_short,
                'short_cpu_hours': short_cpu_hours,
                'total_cpu_hours': total_cpu_hours,
                'pct_cpu_hours_short': pct_cpu_hours,
                'avg_short_runtime_seconds': group_short['runtime_seconds'].mean(),
                'median_short_runtime_seconds': group_short['runtime_seconds'].median(),
                'unique_users': group_short['user'].nunique() if 'user' in group_short.columns else 0
            })

    group_df = pd.DataFrame(group_stats)

    # Sort by number of short jobs
    group_df = group_df.sort_values('short_jobs', ascending=False)

    print(f"  Analyzed {len(group_df)} groups with short jobs")

    return group_df

def analyze_temporal_patterns(df):
    """Analyze temporal patterns of short jobs"""
    print("\nAnalyzing temporal patterns...")

    short_threshold = 300  # 5 minutes
    short_jobs = df[df['runtime_seconds'] <= short_threshold].copy()

    # Hour of day
    short_jobs['hour'] = short_jobs['submit_time'].dt.hour
    hourly = short_jobs.groupby('hour').agg({
        'job_id': 'count',
        'runtime_seconds': ['mean', 'median'],
        'cpus': 'mean'
    }).reset_index()
    hourly.columns = ['hour', 'job_count', 'avg_runtime_seconds', 'median_runtime_seconds', 'avg_cpus']

    # Day of week
    short_jobs['dayofweek'] = short_jobs['submit_time'].dt.dayofweek
    daily = short_jobs.groupby('dayofweek').agg({
        'job_id': 'count',
        'runtime_seconds': ['mean', 'median'],
        'cpus': 'mean'
    }).reset_index()
    daily.columns = ['dayofweek', 'job_count', 'avg_runtime_seconds', 'median_runtime_seconds', 'avg_cpus']
    daily['day_name'] = daily['dayofweek'].map({
        0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday',
        4: 'Friday', 5: 'Saturday', 6: 'Sunday'
    })

    # Combine into single output
    temporal_df = pd.concat([
        hourly.assign(temporal_type='hour_of_day'),
        daily.assign(temporal_type='day_of_week')
    ], ignore_index=True)

    print(f"  Generated temporal patterns for {len(short_jobs):,} short jobs")

    return temporal_df

def detect_job_arrays(df):
    """Detect potential job arrays based on rapid successive submissions"""
    print("\nDetecting job array patterns...")

    if 'user' not in df.columns:
        print("  Warning: No user column found")
        return pd.DataFrame()

    # Sort by user and submit time
    df_sorted = df.sort_values(['user', 'submit_time']).copy()

    arrays_detected = []

    for user in df['user'].unique():
        user_jobs = df_sorted[df_sorted['user'] == user].copy()

        if len(user_jobs) < 2:
            continue

        # Calculate time between successive submissions
        user_jobs['time_since_prev'] = user_jobs['submit_time'].diff().dt.total_seconds()

        # Define job array: multiple jobs submitted within 10 seconds of each other
        # with similar resource requests
        array_threshold = 10  # seconds

        i = 0
        while i < len(user_jobs):
            # Look ahead for jobs submitted close together
            array_jobs = [i]
            j = i + 1

            while j < len(user_jobs):
                time_diff = user_jobs.iloc[j]['time_since_prev']

                if time_diff <= array_threshold:
                    # Check if resources are similar (within 20%)
                    cpu_ratio = user_jobs.iloc[j]['cpus'] / user_jobs.iloc[i]['cpus'] if user_jobs.iloc[i]['cpus'] > 0 else 1
                    mem_ratio = user_jobs.iloc[j]['mem_req'] / user_jobs.iloc[i]['mem_req'] if user_jobs.iloc[i]['mem_req'] > 0 else 1

                    if 0.8 <= cpu_ratio <= 1.2 and 0.8 <= mem_ratio <= 1.2:
                        array_jobs.append(j)
                    else:
                        break
                else:
                    break

                j += 1

            # If we found an array (3+ similar jobs submitted rapidly)
            if len(array_jobs) >= 3:
                array_subset = user_jobs.iloc[array_jobs]

                arrays_detected.append({
                    'user': user,
                    'group': user_jobs.iloc[i]['group'] if 'group' in user_jobs.columns else None,
                    'first_submit_time': array_subset['submit_time'].min(),
                    'array_size': len(array_jobs),
                    'submission_window_seconds': (array_subset['submit_time'].max() - array_subset['submit_time'].min()).total_seconds(),
                    'avg_cpus': array_subset['cpus'].mean(),
                    'avg_mem_mb': array_subset['mem_req'].mean(),
                    'avg_runtime_seconds': array_subset['runtime_seconds'].mean(),
                    'total_cpu_hours': (array_subset['cpus'] * array_subset['runtime_seconds']).sum() / 3600,
                    'avg_wait_seconds': array_subset['wait_seconds'].mean()
                })

                i = j  # Skip past this array
            else:
                i += 1

    arrays_df = pd.DataFrame(arrays_detected)

    if len(arrays_df) > 0:
        arrays_df = arrays_df.sort_values('array_size', ascending=False)
        print(f"  Detected {len(arrays_df):,} potential job arrays")
        print(f"  Largest array: {arrays_df['array_size'].max()} jobs")
        print(f"  Total jobs in arrays: {arrays_df['array_size'].sum():,}")
    else:
        print("  No job arrays detected")

    return arrays_df

def detect_workflow_sequences(df):
    """Detect potential workflow sequences (chains of dependent jobs)"""
    print("\nDetecting workflow sequences...")

    if 'user' not in df.columns:
        print("  Warning: No user column found")
        return pd.DataFrame()

    # Sort by user and time
    df_sorted = df.sort_values(['user', 'submit_time']).copy()

    sequences = []

    for user in df['user'].unique():
        user_jobs = df_sorted[df_sorted['user'] == user].copy()

        if len(user_jobs) < 3:
            continue

        # Look for sequences where jobs start soon after previous job ends
        # (suggesting dependency)
        user_jobs['prev_end_time'] = user_jobs['end_time'].shift(1)
        user_jobs['time_since_prev_end'] = (user_jobs['submit_time'] - user_jobs['prev_end_time']).dt.total_seconds()

        # Define workflow: job submitted within 5 minutes of previous job ending
        workflow_threshold = 300  # 5 minutes

        i = 0
        while i < len(user_jobs):
            sequence_jobs = [i]
            j = i + 1

            while j < len(user_jobs):
                time_since_end = user_jobs.iloc[j]['time_since_prev_end']

                # Check if submitted soon after previous ended (and not NaN)
                if pd.notna(time_since_end) and 0 <= time_since_end <= workflow_threshold:
                    sequence_jobs.append(j)
                else:
                    break

                j += 1

            # If we found a sequence (3+ jobs in chain)
            if len(sequence_jobs) >= 3:
                sequence_subset = user_jobs.iloc[sequence_jobs]

                # Calculate total duration (first submit to last end)
                total_duration = (sequence_subset['end_time'].max() - sequence_subset['submit_time'].min()).total_seconds()

                sequences.append({
                    'user': user,
                    'group': user_jobs.iloc[i]['group'] if 'group' in user_jobs.columns else None,
                    'sequence_start': sequence_subset['submit_time'].min(),
                    'sequence_end': sequence_subset['end_time'].max(),
                    'sequence_length': len(sequence_jobs),
                    'total_duration_seconds': total_duration,
                    'avg_job_runtime_seconds': sequence_subset['runtime_seconds'].mean(),
                    'avg_inter_job_delay_seconds': sequence_subset['time_since_prev_end'].mean(),
                    'total_cpu_hours': (sequence_subset['cpus'] * sequence_subset['runtime_seconds']).sum() / 3600,
                    'is_short_jobs': (sequence_subset['runtime_seconds'] <= 300).mean() > 0.5  # >50% are short
                })

                i = j
            else:
                i += 1

    sequences_df = pd.DataFrame(sequences)

    if len(sequences_df) > 0:
        sequences_df = sequences_df.sort_values('sequence_length', ascending=False)
        print(f"  Detected {len(sequences_df):,} potential workflow sequences")
        print(f"  Longest sequence: {sequences_df['sequence_length'].max()} jobs")

        # Count short job workflows
        short_workflows = sequences_df[sequences_df['is_short_jobs']].shape[0]
        if short_workflows > 0:
            print(f"  Short job workflows: {short_workflows} ({short_workflows/len(sequences_df)*100:.1f}%)")
    else:
        print("  No workflow sequences detected")

    return sequences_df

def calculate_scheduler_overhead(df, arrays_df, sequences_df):
    """Calculate estimated scheduler overhead from short jobs and arrays"""
    print("\nCalculating scheduler overhead impact...")

    # Overall stats
    total_jobs = len(df)

    # Short jobs (< 5 min)
    short_threshold = 300
    short_jobs = df[df['runtime_seconds'] <= short_threshold]
    short_count = len(short_jobs)

    # Very short jobs (< 1 min)
    very_short_jobs = df[df['runtime_seconds'] <= 60]
    very_short_count = len(very_short_jobs)

    # Overhead estimates
    # Assume 3 seconds average scheduler overhead per job
    avg_overhead_per_job = 3  # seconds

    overhead_stats = []

    # Total overhead
    total_overhead_hours = (total_jobs * avg_overhead_per_job) / 3600
    total_cpu_hours = (df['cpus'] * df['runtime_seconds']).sum() / 3600
    total_overhead_pct = (total_overhead_hours / total_cpu_hours) * 100 if total_cpu_hours > 0 else 0

    overhead_stats.append({
        'category': 'all_jobs',
        'job_count': total_jobs,
        'estimated_overhead_hours': total_overhead_hours,
        'useful_cpu_hours': total_cpu_hours,
        'overhead_ratio_pct': total_overhead_pct,
        'description': 'All jobs in dataset'
    })

    # Short jobs overhead
    if short_count > 0:
        short_overhead_hours = (short_count * avg_overhead_per_job) / 3600
        short_cpu_hours = (short_jobs['cpus'] * short_jobs['runtime_seconds']).sum() / 3600
        short_overhead_pct = (short_overhead_hours / short_cpu_hours) * 100 if short_cpu_hours > 0 else 0

        overhead_stats.append({
            'category': 'short_jobs_5min',
            'job_count': short_count,
            'estimated_overhead_hours': short_overhead_hours,
            'useful_cpu_hours': short_cpu_hours,
            'overhead_ratio_pct': short_overhead_pct,
            'description': 'Jobs under 5 minutes'
        })

    # Very short jobs overhead
    if very_short_count > 0:
        very_short_overhead_hours = (very_short_count * avg_overhead_per_job) / 3600
        very_short_cpu_hours = (very_short_jobs['cpus'] * very_short_jobs['runtime_seconds']).sum() / 3600
        very_short_overhead_pct = (very_short_overhead_hours / very_short_cpu_hours) * 100 if very_short_cpu_hours > 0 else 0

        overhead_stats.append({
            'category': 'very_short_jobs_1min',
            'job_count': very_short_count,
            'estimated_overhead_hours': very_short_overhead_hours,
            'useful_cpu_hours': very_short_cpu_hours,
            'overhead_ratio_pct': very_short_overhead_pct,
            'description': 'Jobs under 1 minute'
        })

    # Job arrays overhead impact
    if len(arrays_df) > 0:
        total_array_jobs = arrays_df['array_size'].sum()
        array_overhead_hours = (total_array_jobs * avg_overhead_per_job) / 3600
        array_cpu_hours = arrays_df['total_cpu_hours'].sum()
        array_overhead_pct = (array_overhead_hours / array_cpu_hours) * 100 if array_cpu_hours > 0 else 0

        overhead_stats.append({
            'category': 'job_arrays',
            'job_count': total_array_jobs,
            'estimated_overhead_hours': array_overhead_hours,
            'useful_cpu_hours': array_cpu_hours,
            'overhead_ratio_pct': array_overhead_pct,
            'description': 'Jobs submitted as arrays (rapid succession)'
        })

    # Workflow sequences overhead
    if len(sequences_df) > 0:
        total_sequence_jobs = sequences_df['sequence_length'].sum()
        sequence_overhead_hours = (total_sequence_jobs * avg_overhead_per_job) / 3600
        sequence_cpu_hours = sequences_df['total_cpu_hours'].sum()
        sequence_overhead_pct = (sequence_overhead_hours / sequence_cpu_hours) * 100 if sequence_cpu_hours > 0 else 0

        overhead_stats.append({
            'category': 'workflow_sequences',
            'job_count': total_sequence_jobs,
            'estimated_overhead_hours': sequence_overhead_hours,
            'useful_cpu_hours': sequence_cpu_hours,
            'overhead_ratio_pct': sequence_overhead_pct,
            'description': 'Jobs in workflow sequences (chained dependencies)'
        })

    overhead_df = pd.DataFrame(overhead_stats)

    print(f"  Calculated overhead for {len(overhead_df)} categories")

    return overhead_df

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_short_jobs_and_arrays.py <jobs_csv>")
        print("")
        print("Analyzes short jobs and job arrays to understand scheduler overhead")
        print("and workflow patterns.")
        print("")
        print("Outputs:")
        print("  - short_jobs_summary.csv          - Overall statistics")
        print("  - short_jobs_by_user.csv          - Per-user patterns")
        print("  - short_jobs_by_group.csv         - Per-group patterns")
        print("  - short_jobs_temporal.csv         - Temporal patterns")
        print("  - job_arrays_detected.csv         - Detected job arrays")
        print("  - workflow_sequences.csv          - Workflow sequences")
        print("  - scheduler_overhead_analysis.csv - Overhead estimates")
        sys.exit(1)

    jobs_file = sys.argv[1]

    print("="*70)
    print("SHORT JOBS AND JOB ARRAY ANALYSIS")
    print("="*70)

    # Load data
    df = load_job_data(jobs_file)

    # Analyze short jobs
    summary_df = analyze_short_jobs_summary(df)
    user_df = analyze_short_jobs_by_user(df)
    group_df = analyze_short_jobs_by_group(df)
    temporal_df = analyze_temporal_patterns(df)

    # Detect patterns
    arrays_df = detect_job_arrays(df)
    sequences_df = detect_workflow_sequences(df)

    # Calculate overhead
    overhead_df = calculate_scheduler_overhead(df, arrays_df, sequences_df)

    # Save outputs
    print("\n" + "="*70)
    print("SAVING RESULTS")
    print("="*70)

    summary_df.to_csv('short_jobs_summary.csv', index=False)
    print("  Saved: short_jobs_summary.csv")

    if len(user_df) > 0:
        user_df.to_csv('short_jobs_by_user.csv', index=False)
        print("  Saved: short_jobs_by_user.csv")

    if len(group_df) > 0:
        group_df.to_csv('short_jobs_by_group.csv', index=False)
        print("  Saved: short_jobs_by_group.csv")

    temporal_df.to_csv('short_jobs_temporal.csv', index=False)
    print("  Saved: short_jobs_temporal.csv")

    if len(arrays_df) > 0:
        arrays_df.to_csv('job_arrays_detected.csv', index=False)
        print("  Saved: job_arrays_detected.csv")

    if len(sequences_df) > 0:
        sequences_df.to_csv('workflow_sequences.csv', index=False)
        print("  Saved: workflow_sequences.csv")

    overhead_df.to_csv('scheduler_overhead_analysis.csv', index=False)
    print("  Saved: scheduler_overhead_analysis.csv")

    # Summary statistics
    print("\n" + "="*70)
    print("ANALYSIS SUMMARY")
    print("="*70)

    print("\nShort Jobs (<5 min):")
    short_5min = summary_df[summary_df['threshold'] == 'short_5min'].iloc[0]
    print(f"  Count: {short_5min['job_count']:,} ({short_5min['pct_of_jobs']:.1f}% of all jobs)")
    print(f"  CPU hours: {short_5min['total_cpu_hours']:,.1f} ({short_5min['pct_of_cpu_hours']:.1f}% of total)")
    print(f"  Estimated overhead: {short_5min['estimated_scheduler_overhead_hours']:.1f} hours")
    print(f"  Overhead ratio: {short_5min['overhead_ratio_pct']:.2f}%")

    if len(arrays_df) > 0:
        print(f"\nJob Arrays:")
        print(f"  Detected arrays: {len(arrays_df):,}")
        print(f"  Total jobs in arrays: {arrays_df['array_size'].sum():,}")
        print(f"  Largest array: {arrays_df['array_size'].max()} jobs")
        print(f"  Avg array size: {arrays_df['array_size'].mean():.1f} jobs")

    if len(sequences_df) > 0:
        print(f"\nWorkflow Sequences:")
        print(f"  Detected sequences: {len(sequences_df):,}")
        print(f"  Total jobs in sequences: {sequences_df['sequence_length'].sum():,}")
        print(f"  Longest sequence: {sequences_df['sequence_length'].max()} jobs")
        print(f"  Avg sequence length: {sequences_df['sequence_length'].mean():.1f} jobs")

        short_workflows = sequences_df[sequences_df['is_short_jobs']].shape[0]
        if short_workflows > 0:
            print(f"  Short job workflows: {short_workflows} ({short_workflows/len(sequences_df)*100:.1f}%)")

    print("\n" + "="*70)
    print("COMPLETE")
    print("="*70)

if __name__ == '__main__':
    main()
