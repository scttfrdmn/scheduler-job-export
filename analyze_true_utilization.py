#!/usr/bin/env python3
"""
True Utilization Analysis with Time Series

Calculates utilization at job transition times (start/end) with:
- Node-level: busy/idle status
- CPU-level: allocated CPUs vs total capacity
- Memory-level: allocated memory vs total capacity

Outputs:
- Comprehensive statistics (mean, median, percentiles, etc.)
- Time series CSV for visualization
- Per-metric analysis
"""

import pandas as pd
import sys
from datetime import datetime
import numpy as np

def load_job_data(filename):
    """Load and validate job data"""
    print(f"Loading job data from {filename}...")

    df = pd.read_csv(filename)

    # Convert timestamps
    for col in ['submit_time', 'start_time', 'end_time']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Convert resource columns
    if 'cpus' in df.columns:
        df['cpus'] = pd.to_numeric(df['cpus'], errors='coerce').fillna(1)

    if 'mem_req' in df.columns:
        df['mem_req'] = pd.to_numeric(df['mem_req'], errors='coerce').fillna(0)

    if 'nodes' in df.columns:
        df['nodes'] = pd.to_numeric(df['nodes'], errors='coerce').fillna(1)

    # Filter to jobs that actually ran
    df = df[df['start_time'].notna() & df['end_time'].notna()].copy()

    # Remove jobs with invalid times
    df = df[df['start_time'] < df['end_time']]

    print(f"Loaded {len(df):,} valid jobs")

    return df

def load_cluster_config(filename):
    """Load cluster configuration to get total capacity"""
    print(f"\nLoading cluster configuration from {filename}...")

    try:
        config = pd.read_csv(filename)

        # Try to extract total capacity
        total_cpus = 0
        total_memory_mb = 0
        total_nodes = len(config)

        # Try different column name variations
        cpu_cols = ['cpus', 'CPUs', 'num_proc', 'slots', 'slots_total']
        mem_cols = ['memory_mb', 'mem_total_mb', 'Memory', 'mem_total']

        for col in cpu_cols:
            if col in config.columns:
                total_cpus = pd.to_numeric(config[col], errors='coerce').sum()
                print(f"  Found CPU data in column: {col}")
                break

        for col in mem_cols:
            if col in config.columns:
                total_memory_mb = pd.to_numeric(config[col], errors='coerce').sum()
                print(f"  Found memory data in column: {col}")
                break

        print(f"\nCluster Capacity:")
        print(f"  Total Nodes: {total_nodes:,}")
        print(f"  Total CPUs: {total_cpus:,}")
        print(f"  Total Memory: {total_memory_mb/1024/1024:.1f} TB")

        return {
            'total_nodes': total_nodes,
            'total_cpus': int(total_cpus),
            'total_memory_mb': int(total_memory_mb)
        }

    except FileNotFoundError:
        print(f"Warning: Cluster config file not found: {filename}")
        print("Capacity-based utilization will not be calculated.")
        return None

def calculate_utilization_timeseries(df, cluster_config):
    """Calculate utilization at every job transition time"""
    print("\nCalculating utilization time series...")

    # Create events for job starts and ends
    events = []

    for _, job in df.iterrows():
        # Job start event
        events.append({
            'timestamp': job['start_time'],
            'event_type': 'start',
            'cpus': job['cpus'],
            'memory_mb': job['mem_req'],
            'nodes': job['nodes']
        })

        # Job end event
        events.append({
            'timestamp': job['end_time'],
            'event_type': 'end',
            'cpus': job['cpus'],
            'memory_mb': job['mem_req'],
            'nodes': job['nodes']
        })

    # Convert to DataFrame and sort by time
    events_df = pd.DataFrame(events)
    events_df = events_df.sort_values('timestamp').reset_index(drop=True)

    print(f"Processing {len(events_df):,} events...")

    # Calculate running totals at each event
    timeseries = []

    current_cpus = 0
    current_memory_mb = 0
    current_nodes_with_jobs = set()

    for idx, event in events_df.iterrows():
        # Update state
        if event['event_type'] == 'start':
            current_cpus += event['cpus']
            current_memory_mb += event['memory_mb']
            # Nodes is tricky - we approximate
        else:  # end
            current_cpus -= event['cpus']
            current_memory_mb -= event['memory_mb']

        # Ensure non-negative (floating point errors)
        current_cpus = max(0, current_cpus)
        current_memory_mb = max(0, current_memory_mb)

        # Calculate utilization percentages
        cpu_util = 0
        memory_util = 0

        if cluster_config:
            if cluster_config['total_cpus'] > 0:
                cpu_util = (current_cpus / cluster_config['total_cpus']) * 100

            if cluster_config['total_memory_mb'] > 0:
                memory_util = (current_memory_mb / cluster_config['total_memory_mb']) * 100

        timeseries.append({
            'timestamp': event['timestamp'],
            'event_type': event['event_type'],
            'cpus_allocated': current_cpus,
            'memory_allocated_mb': current_memory_mb,
            'cpu_utilization_pct': cpu_util,
            'memory_utilization_pct': memory_util
        })

        # Progress indicator
        if (idx + 1) % 50000 == 0:
            print(f"  Processed {idx+1:,} / {len(events_df):,} events...")

    ts_df = pd.DataFrame(timeseries)

    print(f"Generated {len(ts_df):,} time series points")

    return ts_df

def calculate_statistics(ts_df, cluster_config):
    """Calculate comprehensive statistics"""
    print("\n" + "="*80)
    print("UTILIZATION STATISTICS")
    print("="*80)

    stats = {}

    # CPU Utilization
    if 'cpu_utilization_pct' in ts_df.columns:
        cpu_util = ts_df['cpu_utilization_pct']

        print("\nCPU Utilization:")
        print(f"  Mean:        {cpu_util.mean():>8.2f}%")
        print(f"  Median:      {cpu_util.median():>8.2f}%")
        print(f"  Std Dev:     {cpu_util.std():>8.2f}%")
        print(f"  Min:         {cpu_util.min():>8.2f}%")
        print(f"  Max:         {cpu_util.max():>8.2f}%")
        print(f"  25th %ile:   {cpu_util.quantile(0.25):>8.2f}%")
        print(f"  75th %ile:   {cpu_util.quantile(0.75):>8.2f}%")
        print(f"  90th %ile:   {cpu_util.quantile(0.90):>8.2f}%")
        print(f"  95th %ile:   {cpu_util.quantile(0.95):>8.2f}%")
        print(f"  99th %ile:   {cpu_util.quantile(0.99):>8.2f}%")

        stats['cpu'] = {
            'mean': cpu_util.mean(),
            'median': cpu_util.median(),
            'std': cpu_util.std(),
            'min': cpu_util.min(),
            'max': cpu_util.max(),
            'p25': cpu_util.quantile(0.25),
            'p75': cpu_util.quantile(0.75),
            'p90': cpu_util.quantile(0.90),
            'p95': cpu_util.quantile(0.95),
            'p99': cpu_util.quantile(0.99)
        }

    # Memory Utilization
    if 'memory_utilization_pct' in ts_df.columns:
        mem_util = ts_df['memory_utilization_pct']

        print("\nMemory Utilization:")
        print(f"  Mean:        {mem_util.mean():>8.2f}%")
        print(f"  Median:      {mem_util.median():>8.2f}%")
        print(f"  Std Dev:     {mem_util.std():>8.2f}%")
        print(f"  Min:         {mem_util.min():>8.2f}%")
        print(f"  Max:         {mem_util.max():>8.2f}%")
        print(f"  25th %ile:   {mem_util.quantile(0.25):>8.2f}%")
        print(f"  75th %ile:   {mem_util.quantile(0.75):>8.2f}%")
        print(f"  90th %ile:   {mem_util.quantile(0.90):>8.2f}%")
        print(f"  95th %ile:   {mem_util.quantile(0.95):>8.2f}%")
        print(f"  99th %ile:   {mem_util.quantile(0.99):>8.2f}%")

        stats['memory'] = {
            'mean': mem_util.mean(),
            'median': mem_util.median(),
            'std': mem_util.std(),
            'min': mem_util.min(),
            'max': mem_util.max(),
            'p25': mem_util.quantile(0.25),
            'p75': mem_util.quantile(0.75),
            'p90': mem_util.quantile(0.90),
            'p95': mem_util.quantile(0.95),
            'p99': mem_util.quantile(0.99)
        }

    # Absolute allocations
    if 'cpus_allocated' in ts_df.columns:
        cpus_alloc = ts_df['cpus_allocated']

        print("\nCPU Allocation (absolute):")
        print(f"  Mean:        {cpus_alloc.mean():>12,.0f} CPUs")
        print(f"  Median:      {cpus_alloc.median():>12,.0f} CPUs")
        print(f"  Peak:        {cpus_alloc.max():>12,.0f} CPUs")

        if cluster_config:
            print(f"  Capacity:    {cluster_config['total_cpus']:>12,} CPUs")

    if 'memory_allocated_mb' in ts_df.columns:
        mem_alloc = ts_df['memory_allocated_mb']

        print("\nMemory Allocation (absolute):")
        print(f"  Mean:        {mem_alloc.mean()/1024/1024:>12,.1f} TB")
        print(f"  Median:      {mem_alloc.median()/1024/1024:>12,.1f} TB")
        print(f"  Peak:        {mem_alloc.max()/1024/1024:>12,.1f} TB")

        if cluster_config:
            print(f"  Capacity:    {cluster_config['total_memory_mb']/1024/1024:>12,.1f} TB")

    # Time-weighted averages
    print("\nTime-Weighted Utilization:")
    if len(ts_df) > 1:
        # Calculate time deltas
        ts_df_sorted = ts_df.sort_values('timestamp').copy()
        ts_df_sorted['time_delta'] = ts_df_sorted['timestamp'].diff().dt.total_seconds()

        # Drop first row (no delta)
        ts_df_sorted = ts_df_sorted.iloc[1:].copy()

        total_time = ts_df_sorted['time_delta'].sum()

        if total_time > 0:
            cpu_time_weighted = (ts_df_sorted['cpu_utilization_pct'] * ts_df_sorted['time_delta']).sum() / total_time
            mem_time_weighted = (ts_df_sorted['memory_utilization_pct'] * ts_df_sorted['time_delta']).sum() / total_time

            print(f"  CPU (time-weighted):    {cpu_time_weighted:>8.2f}%")
            print(f"  Memory (time-weighted): {mem_time_weighted:>8.2f}%")

            stats['time_weighted'] = {
                'cpu': cpu_time_weighted,
                'memory': mem_time_weighted
            }

    print()
    print("="*80)

    return stats

def save_timeseries(ts_df, filename):
    """Save time series to CSV for visualization"""
    print(f"\nSaving time series to {filename}...")

    # Sort by timestamp
    ts_df = ts_df.sort_values('timestamp').copy()

    # Format timestamp as string for better CSV compatibility
    ts_df['timestamp_str'] = ts_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Reorder columns
    output_cols = [
        'timestamp_str',
        'timestamp',
        'event_type',
        'cpus_allocated',
        'cpu_utilization_pct',
        'memory_allocated_mb',
        'memory_utilization_pct'
    ]

    # Only include columns that exist
    output_cols = [col for col in output_cols if col in ts_df.columns]

    ts_df[output_cols].to_csv(filename, index=False)

    print(f"  Saved {len(ts_df):,} time series points")
    print(f"  Columns: {', '.join(output_cols)}")

def save_statistics(stats, filename):
    """Save statistics summary to CSV"""
    print(f"\nSaving statistics to {filename}...")

    rows = []

    # CPU stats
    if 'cpu' in stats:
        for metric, value in stats['cpu'].items():
            rows.append({
                'resource': 'CPU',
                'metric': metric,
                'value': value,
                'unit': 'percent'
            })

    # Memory stats
    if 'memory' in stats:
        for metric, value in stats['memory'].items():
            rows.append({
                'resource': 'Memory',
                'metric': metric,
                'value': value,
                'unit': 'percent'
            })

    # Time-weighted
    if 'time_weighted' in stats:
        rows.append({
            'resource': 'CPU',
            'metric': 'time_weighted',
            'value': stats['time_weighted']['cpu'],
            'unit': 'percent'
        })
        rows.append({
            'resource': 'Memory',
            'metric': 'time_weighted',
            'value': stats['time_weighted']['memory'],
            'unit': 'percent'
        })

    stats_df = pd.DataFrame(rows)
    stats_df.to_csv(filename, index=False)

    print(f"  Saved {len(stats_df)} statistics")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_true_utilization.py <jobs_csv> [cluster_config_csv]")
        print("")
        print("Calculates true utilization with comprehensive statistics and time series.")
        print("")
        print("Arguments:")
        print("  jobs_csv           - Anonymized job data CSV")
        print("  cluster_config_csv - Cluster configuration CSV (optional, for capacity)")
        print("")
        print("Outputs:")
        print("  utilization_timeseries.csv - Time series data for visualization")
        print("  utilization_statistics.csv - Summary statistics")
        sys.exit(1)

    jobs_file = sys.argv[1]
    config_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Load data
    df = load_job_data(jobs_file)

    cluster_config = None
    if config_file:
        cluster_config = load_cluster_config(config_file)
    else:
        print("\nWarning: No cluster config provided.")
        print("Utilization percentages cannot be calculated without total capacity.")
        print("Only absolute allocations will be shown.")

    # Calculate time series
    ts_df = calculate_utilization_timeseries(df, cluster_config)

    # Calculate statistics
    stats = calculate_statistics(ts_df, cluster_config)

    # Save outputs
    save_timeseries(ts_df, 'utilization_timeseries.csv')
    save_statistics(stats, 'utilization_statistics.csv')

    print("\n" + "="*80)
    print("OUTPUTS CREATED")
    print("="*80)
    print("\nTime Series (for visualization):")
    print("  utilization_timeseries.csv")
    print("    - Timestamp at each job start/end")
    print("    - CPU and memory allocation")
    print("    - Utilization percentages")
    print("    - Ready for plotting in Python, R, Excel, etc.")
    print("")
    print("Statistics Summary:")
    print("  utilization_statistics.csv")
    print("    - Mean, median, percentiles")
    print("    - Time-weighted averages")
    print("    - For both CPU and memory")
    print("")
    print("Visualization Examples:")
    print("  Python/matplotlib:")
    print("    import pandas as pd")
    print("    import matplotlib.pyplot as plt")
    print("    df = pd.read_csv('utilization_timeseries.csv', parse_dates=['timestamp'])")
    print("    plt.plot(df['timestamp'], df['cpu_utilization_pct'])")
    print("    plt.xlabel('Time')")
    print("    plt.ylabel('CPU Utilization (%)')")
    print("    plt.show()")
    print("")
    print("  Excel:")
    print("    - Open utilization_timeseries.csv")
    print("    - Create scatter or line chart")
    print("    - X-axis: timestamp, Y-axis: cpu_utilization_pct")
    print("")
    print("="*80)

if __name__ == '__main__':
    main()
