#!/usr/bin/env python3
"""
Job-Level Resource Efficiency Analysis

Analyzes requested vs actually used resources for:
- CPUs/cores
- Memory
- GPUs
- Data I/O

Provides per-user and per-group efficiency metrics to identify:
- Over-requesting (waste)
- Under-requesting (performance issues)
- Optimal resource requesters

Outputs time series for tracking efficiency trends.
"""

import pandas as pd
import sys
import numpy as np
from datetime import datetime

def load_job_data(filename):
    """Load job data with resource information"""
    print(f"Loading job data from {filename}...")

    df = pd.read_csv(filename)

    # Parse timestamps
    for col in ['submit_time', 'start_time', 'end_time']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Parse resource columns
    numeric_cols = {
        'cpus': 1,
        'mem_req': 0,
        'nodes': 1,
        'cpus_alloc': None,
        'mem_used': None,
        'mem_used_max': None,
        'cpu_efficiency_pct': None,
        'mem_efficiency_pct': None,
        'gpu_req': 0,
        'gpu_used': None
    }

    for col, default in numeric_cols.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            if default is not None:
                df[col] = df[col].fillna(default)

    # Calculate runtime
    if 'start_time' in df.columns and 'end_time' in df.columns:
        df['runtime_hours'] = (df['end_time'] - df['start_time']).dt.total_seconds() / 3600
        df = df[df['runtime_hours'] > 0]  # Remove invalid runtimes

    print(f"Loaded {len(df):,} jobs")
    print(f"Columns available: {', '.join(df.columns)}")

    return df

def calculate_efficiency_metrics(df):
    """Calculate resource efficiency metrics"""
    print("\nCalculating efficiency metrics...")

    # CPU Efficiency
    if 'cpus' in df.columns and 'cpu_efficiency_pct' in df.columns:
        df['cpu_efficiency'] = df['cpu_efficiency_pct']
    elif 'cpus' in df.columns and 'cpus_alloc' in df.columns:
        # If we have allocated vs requested
        df['cpu_efficiency'] = (df['cpus_alloc'] / df['cpus'] * 100).clip(0, 100)
    else:
        df['cpu_efficiency'] = np.nan

    # Memory Efficiency
    if 'mem_efficiency_pct' in df.columns:
        df['mem_efficiency'] = df['mem_efficiency_pct']
    elif 'mem_req' in df.columns and 'mem_used_max' in df.columns:
        # Max memory used vs requested
        df['mem_efficiency'] = (df['mem_used_max'] / df['mem_req'] * 100).clip(0, 100)
        df.loc[df['mem_req'] == 0, 'mem_efficiency'] = np.nan
    elif 'mem_req' in df.columns and 'mem_used' in df.columns:
        # Average memory used vs requested
        df['mem_efficiency'] = (df['mem_used'] / df['mem_req'] * 100).clip(0, 100)
        df.loc[df['mem_req'] == 0, 'mem_efficiency'] = np.nan
    else:
        df['mem_efficiency'] = np.nan

    # GPU Efficiency (if available)
    if 'gpu_req' in df.columns and 'gpu_used' in df.columns:
        df['gpu_efficiency'] = (df['gpu_used'] / df['gpu_req'] * 100).clip(0, 100)
        df.loc[df['gpu_req'] == 0, 'gpu_efficiency'] = np.nan
    else:
        df['gpu_efficiency'] = np.nan

    # Calculate waste (over-requesting)
    if 'cpus' in df.columns and not pd.isna(df['cpu_efficiency']).all():
        df['cpu_waste_pct'] = 100 - df['cpu_efficiency']

    if 'mem_req' in df.columns and not pd.isna(df['mem_efficiency']).all():
        df['mem_waste_pct'] = 100 - df['mem_efficiency']

    # Calculate CPU-hours wasted
    if 'runtime_hours' in df.columns and 'cpus' in df.columns and 'cpu_waste_pct' in df.columns:
        df['cpu_hours_wasted'] = df['runtime_hours'] * df['cpus'] * (df['cpu_waste_pct'] / 100)

    valid_cpu = df['cpu_efficiency'].notna().sum()
    valid_mem = df['mem_efficiency'].notna().sum()

    print(f"  Jobs with CPU efficiency data: {valid_cpu:,}")
    print(f"  Jobs with memory efficiency data: {valid_mem:,}")

    return df

def analyze_per_user(df):
    """Analyze efficiency by user"""
    print("\nAnalyzing per-user efficiency...")

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
            'total_cpu_hours': 0,
            'cpu_efficiency_mean': np.nan,
            'cpu_efficiency_median': np.nan,
            'mem_efficiency_mean': np.nan,
            'mem_efficiency_median': np.nan,
            'cpu_hours_wasted': 0,
            'jobs_with_low_cpu_eff': 0,
            'jobs_with_low_mem_eff': 0
        }

        # CPU stats
        if 'runtime_hours' in user_jobs.columns and 'cpus' in user_jobs.columns:
            stats['total_cpu_hours'] = (user_jobs['runtime_hours'] * user_jobs['cpus']).sum()

        if 'cpu_efficiency' in user_jobs.columns:
            cpu_eff = user_jobs['cpu_efficiency'].dropna()
            if len(cpu_eff) > 0:
                stats['cpu_efficiency_mean'] = cpu_eff.mean()
                stats['cpu_efficiency_median'] = cpu_eff.median()
                stats['jobs_with_low_cpu_eff'] = (cpu_eff < 50).sum()

        if 'cpu_hours_wasted' in user_jobs.columns:
            stats['cpu_hours_wasted'] = user_jobs['cpu_hours_wasted'].sum()

        # Memory stats
        if 'mem_efficiency' in user_jobs.columns:
            mem_eff = user_jobs['mem_efficiency'].dropna()
            if len(mem_eff) > 0:
                stats['mem_efficiency_mean'] = mem_eff.mean()
                stats['mem_efficiency_median'] = mem_eff.median()
                stats['jobs_with_low_mem_eff'] = (mem_eff < 50).sum()

        user_stats.append(stats)

    user_df = pd.DataFrame(user_stats)
    user_df = user_df.sort_values('total_cpu_hours', ascending=False)

    print(f"  Analyzed {len(user_df)} users")

    return user_df

def analyze_per_group(df):
    """Analyze efficiency by group"""
    print("\nAnalyzing per-group efficiency...")

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
            'total_cpu_hours': 0,
            'cpu_efficiency_mean': np.nan,
            'mem_efficiency_mean': np.nan,
            'cpu_hours_wasted': 0
        }

        # CPU stats
        if 'runtime_hours' in group_jobs.columns and 'cpus' in group_jobs.columns:
            stats['total_cpu_hours'] = (group_jobs['runtime_hours'] * group_jobs['cpus']).sum()

        if 'cpu_efficiency' in group_jobs.columns:
            cpu_eff = group_jobs['cpu_efficiency'].dropna()
            if len(cpu_eff) > 0:
                stats['cpu_efficiency_mean'] = cpu_eff.mean()

        if 'cpu_hours_wasted' in group_jobs.columns:
            stats['cpu_hours_wasted'] = group_jobs['cpu_hours_wasted'].sum()

        # Memory stats
        if 'mem_efficiency' in group_jobs.columns:
            mem_eff = group_jobs['mem_efficiency'].dropna()
            if len(mem_eff) > 0:
                stats['mem_efficiency_mean'] = mem_eff.mean()

        group_stats.append(stats)

    group_df = pd.DataFrame(group_stats)
    group_df = group_df.sort_values('total_cpu_hours', ascending=False)

    print(f"  Analyzed {len(group_df)} groups")

    return group_df

def analyze_efficiency_over_time(df):
    """Track efficiency trends over time"""
    print("\nAnalyzing efficiency trends over time...")

    if 'end_time' not in df.columns:
        print("  Warning: No 'end_time' column found")
        return None

    # Group by week
    df['week'] = df['end_time'].dt.to_period('W')

    weekly_stats = []

    for week in df['week'].dropna().unique():
        week_jobs = df[df['week'] == week]

        stats = {
            'week_start': week.start_time,
            'week': str(week),
            'total_jobs': len(week_jobs),
            'cpu_efficiency_mean': np.nan,
            'mem_efficiency_mean': np.nan,
            'total_cpu_hours': 0,
            'cpu_hours_wasted': 0
        }

        if 'runtime_hours' in week_jobs.columns and 'cpus' in week_jobs.columns:
            stats['total_cpu_hours'] = (week_jobs['runtime_hours'] * week_jobs['cpus']).sum()

        if 'cpu_efficiency' in week_jobs.columns:
            cpu_eff = week_jobs['cpu_efficiency'].dropna()
            if len(cpu_eff) > 0:
                stats['cpu_efficiency_mean'] = cpu_eff.mean()

        if 'mem_efficiency' in week_jobs.columns:
            mem_eff = week_jobs['mem_efficiency'].dropna()
            if len(mem_eff) > 0:
                stats['mem_efficiency_mean'] = mem_eff.mean()

        if 'cpu_hours_wasted' in week_jobs.columns:
            stats['cpu_hours_wasted'] = week_jobs['cpu_hours_wasted'].sum()

        weekly_stats.append(stats)

    weekly_df = pd.DataFrame(weekly_stats)
    weekly_df = weekly_df.sort_values('week_start')

    print(f"  Analyzed {len(weekly_df)} weeks")

    return weekly_df

def print_summary_statistics(df, user_df, group_df):
    """Print summary statistics"""
    print("\n" + "="*80)
    print("RESOURCE EFFICIENCY SUMMARY")
    print("="*80)

    # Overall efficiency
    print("\nOverall Efficiency:")

    if 'cpu_efficiency' in df.columns:
        cpu_eff = df['cpu_efficiency'].dropna()
        if len(cpu_eff) > 0:
            print(f"  CPU Efficiency:")
            print(f"    Mean:       {cpu_eff.mean():>6.1f}%")
            print(f"    Median:     {cpu_eff.median():>6.1f}%")
            print(f"    Std Dev:    {cpu_eff.std():>6.1f}%")
            print(f"    25th %ile:  {cpu_eff.quantile(0.25):>6.1f}%")
            print(f"    75th %ile:  {cpu_eff.quantile(0.75):>6.1f}%")

            low_eff = (cpu_eff < 50).sum()
            print(f"    Jobs < 50%: {low_eff:>6,} ({low_eff/len(cpu_eff)*100:.1f}%)")

    if 'mem_efficiency' in df.columns:
        mem_eff = df['mem_efficiency'].dropna()
        if len(mem_eff) > 0:
            print(f"\n  Memory Efficiency:")
            print(f"    Mean:       {mem_eff.mean():>6.1f}%")
            print(f"    Median:     {mem_eff.median():>6.1f}%")
            print(f"    Std Dev:    {mem_eff.std():>6.1f}%")
            print(f"    25th %ile:  {mem_eff.quantile(0.25):>6.1f}%")
            print(f"    75th %ile:  {mem_eff.quantile(0.75):>6.1f}%")

            low_eff = (mem_eff < 50).sum()
            print(f"    Jobs < 50%: {low_eff:>6,} ({low_eff/len(mem_eff)*100:.1f}%)")

    # Resource waste
    print("\nResource Waste:")

    if 'cpu_hours_wasted' in df.columns:
        total_wasted = df['cpu_hours_wasted'].sum()
        print(f"  Total CPU-hours wasted: {total_wasted:>12,.0f}")

        if 'runtime_hours' in df.columns and 'cpus' in df.columns:
            total_cpu_hours = (df['runtime_hours'] * df['cpus']).sum()
            waste_pct = total_wasted / total_cpu_hours * 100
            print(f"  Percentage wasted:      {waste_pct:>12.1f}%")

    # Top inefficient users
    if user_df is not None and len(user_df) > 0:
        print("\nMost Inefficient Users (by CPU-hours wasted):")
        top_waste = user_df.nlargest(10, 'cpu_hours_wasted')
        for idx, row in top_waste.iterrows():
            print(f"  {row['user']:20s}: {row['cpu_hours_wasted']:>10,.0f} CPU-hours wasted "
                  f"({row['cpu_efficiency_mean']:>5.1f}% avg efficiency)")

    # Top efficient users
    if user_df is not None and len(user_df) > 0:
        print("\nMost Efficient Users (by average CPU efficiency, min 100 jobs):")
        efficient_users = user_df[user_df['total_jobs'] >= 100]
        if len(efficient_users) > 0:
            top_eff = efficient_users.nlargest(10, 'cpu_efficiency_mean')
            for idx, row in top_eff.iterrows():
                print(f"  {row['user']:20s}: {row['cpu_efficiency_mean']:>5.1f}% avg efficiency "
                      f"({row['total_jobs']:,} jobs)")

    print()
    print("="*80)

def save_results(df, user_df, group_df, weekly_df):
    """Save analysis results"""
    print("\nSaving results...")

    # Save per-job efficiency
    if 'cpu_efficiency' in df.columns or 'mem_efficiency' in df.columns:
        output_cols = ['user', 'group', 'job_id', 'end_time', 'runtime_hours',
                      'cpus', 'mem_req', 'cpu_efficiency', 'mem_efficiency',
                      'cpu_waste_pct', 'mem_waste_pct', 'cpu_hours_wasted']
        output_cols = [col for col in output_cols if col in df.columns]

        df[output_cols].to_csv('job_efficiency.csv', index=False)
        print(f"  Saved job_efficiency.csv ({len(df):,} jobs)")

    # Save per-user stats
    if user_df is not None:
        user_df.to_csv('user_efficiency.csv', index=False)
        print(f"  Saved user_efficiency.csv ({len(user_df):,} users)")

    # Save per-group stats
    if group_df is not None:
        group_df.to_csv('group_efficiency.csv', index=False)
        print(f"  Saved group_efficiency.csv ({len(group_df):,} groups)")

    # Save weekly trends
    if weekly_df is not None:
        weekly_df.to_csv('efficiency_trends.csv', index=False)
        print(f"  Saved efficiency_trends.csv ({len(weekly_df):,} weeks)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_job_resource_efficiency.py <jobs_csv>")
        print("")
        print("Analyzes requested vs actually used resources per job, user, and group.")
        print("")
        print("Required CSV columns:")
        print("  - user, group (for grouping)")
        print("  - start_time, end_time (for duration)")
        print("  - cpus, mem_req (requested resources)")
        print("")
        print("Optional columns (for efficiency calculation):")
        print("  - cpu_efficiency_pct or cpus_alloc (actual CPU usage)")
        print("  - mem_efficiency_pct or mem_used_max (actual memory usage)")
        print("  - gpu_req, gpu_used (GPU usage)")
        print("")
        print("Outputs:")
        print("  - job_efficiency.csv - Per-job efficiency metrics")
        print("  - user_efficiency.csv - Per-user summary")
        print("  - group_efficiency.csv - Per-group summary")
        print("  - efficiency_trends.csv - Weekly trends")
        sys.exit(1)

    jobs_file = sys.argv[1]

    # Load and process data
    df = load_job_data(jobs_file)
    df = calculate_efficiency_metrics(df)

    # Analyze by user and group
    user_df = analyze_per_user(df)
    group_df = analyze_per_group(df)

    # Analyze trends
    weekly_df = analyze_efficiency_over_time(df)

    # Print summary
    print_summary_statistics(df, user_df, group_df)

    # Save results
    save_results(df, user_df, group_df, weekly_df)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nOutput files:")
    print("  job_efficiency.csv      - Per-job efficiency metrics")
    print("  user_efficiency.csv     - Per-user aggregates")
    print("  group_efficiency.csv    - Per-group aggregates")
    print("  efficiency_trends.csv   - Weekly time series")
    print("")
    print("Use these files to:")
    print("  - Identify users who over-request resources")
    print("  - Track efficiency improvements over time")
    print("  - Educate users on right-sizing jobs")
    print("  - Calculate resource waste and potential savings")
    print("")
    print("="*80)

if __name__ == '__main__':
    main()
