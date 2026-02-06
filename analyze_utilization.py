#!/usr/bin/env python3
"""
Analyze cluster size, configuration, and utilization from job data
"""

import pandas as pd
import numpy as np
import re
from collections import defaultdict
from datetime import datetime, timedelta

def expand_nodelist(nodelist_str):
    """
    Expand SLURM nodelist format into individual nodes
    e.g., 'node[1935-1937,1939-1940,1950]' -> ['node1935', 'node1936', 'node1937', 'node1939', 'node1940', 'node1950']
    """
    if pd.isna(nodelist_str) or nodelist_str == '':
        return []

    nodes = []

    # Pattern for node ranges: prefix[range1,range2,...]
    range_pattern = r'(\w+)\[([\d,\-]+)\]'
    match = re.match(range_pattern, nodelist_str)

    if match:
        prefix = match.group(1)
        ranges = match.group(2)

        for part in ranges.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                nodes.extend([f"{prefix}{i}" for i in range(start, end + 1)])
            else:
                nodes.append(f"{prefix}{part}")
    else:
        # Simple node name
        nodes.append(nodelist_str)

    return nodes

def analyze_cluster(csv_file):
    """Analyze cluster configuration and utilization"""

    print("Loading job data...")
    print("=" * 80)

    # Read CSV
    chunk_size = 100000
    chunks = []
    for i, chunk in enumerate(pd.read_csv(csv_file, chunksize=chunk_size)):
        chunks.append(chunk)
        if (i + 1) % 10 == 0:
            print(f"Loaded {(i+1)*chunk_size:,} rows...")

    df = pd.concat(chunks, ignore_index=True)
    print(f"Total jobs loaded: {len(df):,}\n")

    # Parse timestamps
    df['submit_time'] = pd.to_datetime(df['submit_time'])
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'])
    df['run_time'] = (df['end_time'] - df['start_time']).dt.total_seconds() / 3600  # hours

    # Filter out invalid durations
    df = df[(df['run_time'] >= 0) & (df['run_time'] < 100000)]

    print("=" * 80)
    print("CLUSTER CONFIGURATION ANALYSIS")
    print("=" * 80)

    # Extract all unique nodes
    print("\nExtracting unique nodes from nodelist...")
    all_nodes = set()
    node_job_counts = defaultdict(int)

    for idx, row in df.iterrows():
        if idx % 500000 == 0 and idx > 0:
            print(f"  Processed {idx:,} jobs...")
        nodes = expand_nodelist(row['nodelist'])
        for node in nodes:
            all_nodes.add(node)
            node_job_counts[node] += 1

    print(f"\nTotal unique nodes discovered: {len(all_nodes)}")

    # Categorize nodes by type
    node_types = defaultdict(set)
    for node in all_nodes:
        # Extract prefix (e.g., 'node', 'gpu')
        match = re.match(r'([a-zA-Z]+)', node)
        if match:
            prefix = match.group(1)
            node_types[prefix].add(node)

    print(f"\nNode types discovered:")
    for node_type, nodes in sorted(node_types.items()):
        print(f"  {node_type}: {len(nodes)} nodes")

    # Analyze node ranges
    print(f"\nNode ID ranges by type:")
    for node_type, nodes in sorted(node_types.items()):
        node_ids = []
        for node in nodes:
            match = re.search(r'(\d+)$', node)
            if match:
                node_ids.append(int(match.group(1)))
        if node_ids:
            node_ids.sort()
            print(f"  {node_type}: {min(node_ids)} - {max(node_ids)} (count: {len(node_ids)})")

    # Estimate CPUs per node type by looking at single-node jobs
    print(f"\n" + "=" * 80)
    print("ESTIMATING NODE CONFIGURATION")
    print("=" * 80)

    single_node_jobs = df[df['nodes_alloc'] == 1].copy()
    print(f"\nAnalyzing {len(single_node_jobs):,} single-node jobs to estimate CPU counts...")

    node_cpu_estimates = {}

    for node_type, nodes in sorted(node_types.items()):
        # Find jobs that ran on this node type
        type_jobs = single_node_jobs[single_node_jobs['nodelist'].str.startswith(node_type)]

        if len(type_jobs) > 0:
            # Look at the distribution of CPUs requested
            cpu_counts = type_jobs['cpus_req'].value_counts()

            # The max CPUs requested on single nodes is likely the node capacity
            max_cpus = type_jobs['cpus_req'].max()

            # Look for common "full node" allocations
            top_cpus = cpu_counts.nlargest(5)

            # Estimate: likely to be a power of 2 or common HPC config
            common_configs = [16, 20, 24, 28, 32, 36, 40, 44, 48, 52, 64, 96, 128]

            # Find the most likely configuration
            likely_config = max_cpus
            for config in common_configs:
                if max_cpus <= config:
                    likely_config = config
                    break

            node_cpu_estimates[node_type] = {
                'max_cpus_seen': max_cpus,
                'likely_cpus': likely_config,
                'sample_size': len(type_jobs),
                'mean_cpus_used': type_jobs['cpus_req'].mean()
            }

            print(f"\n{node_type} nodes ({len(nodes)} nodes):")
            print(f"  Max CPUs seen: {max_cpus}")
            print(f"  Likely CPUs per node: {likely_config}")
            print(f"  Mean CPUs used: {type_jobs['cpus_req'].mean():.2f}")
            print(f"  Sample size: {len(type_jobs):,} jobs")

    # Calculate total cluster size
    print(f"\n" + "=" * 80)
    print("ESTIMATED CLUSTER SIZE")
    print("=" * 80)

    total_cpus = 0
    for node_type, nodes in sorted(node_types.items()):
        if node_type in node_cpu_estimates:
            cpus = node_cpu_estimates[node_type]['likely_cpus']
            type_total = len(nodes) * cpus
            total_cpus += type_total
            print(f"{node_type}: {len(nodes)} nodes × {cpus} CPUs = {type_total:,} CPUs")

    print(f"\nEstimated total cluster CPUs: {total_cpus:,}")

    # Calculate utilization
    print(f"\n" + "=" * 80)
    print("CLUSTER UTILIZATION ANALYSIS")
    print("=" * 80)

    # Time period
    start_date = df['start_time'].min()
    end_date = df['end_time'].max()
    total_days = (end_date - start_date).total_seconds() / 86400
    total_hours = total_days * 24

    print(f"\nTime period analyzed:")
    print(f"  Start: {start_date}")
    print(f"  End: {end_date}")
    print(f"  Duration: {total_days:.1f} days ({total_hours:.1f} hours)")

    # Calculate CPU-hours used
    df['cpu_hours'] = df['cpus_req'] * df['run_time']
    total_cpu_hours = df['cpu_hours'].sum()

    # Calculate theoretical maximum
    theoretical_max = total_cpus * total_hours

    # Overall utilization
    utilization = (total_cpu_hours / theoretical_max) * 100

    print(f"\nCPU-hours consumed: {total_cpu_hours:,.0f}")
    print(f"Theoretical maximum: {theoretical_max:,.0f}")
    print(f"\n*** OVERALL CPU UTILIZATION: {utilization:.2f}% ***")

    # Calculate utilization by node type
    print(f"\n" + "=" * 80)
    print("UTILIZATION BY NODE TYPE")
    print("=" * 80)

    for node_type, nodes in sorted(node_types.items()):
        if node_type not in node_cpu_estimates:
            continue

        # Find jobs that used this node type
        type_jobs = df[df['nodelist'].str.contains(node_type, regex=False, na=False)].copy()

        if len(type_jobs) == 0:
            continue

        type_cpu_hours = type_jobs['cpu_hours'].sum()
        type_total_cpus = len(nodes) * node_cpu_estimates[node_type]['likely_cpus']
        type_theoretical_max = type_total_cpus * total_hours
        type_utilization = (type_cpu_hours / type_theoretical_max) * 100

        print(f"\n{node_type} nodes:")
        print(f"  Nodes: {len(nodes)}")
        print(f"  Total CPUs: {type_total_cpus:,}")
        print(f"  CPU-hours consumed: {type_cpu_hours:,.0f}")
        print(f"  Theoretical maximum: {type_theoretical_max:,.0f}")
        print(f"  Utilization: {type_utilization:.2f}%")
        print(f"  Jobs: {len(type_jobs):,}")

    # Most and least used nodes
    print(f"\n" + "=" * 80)
    print("NODE USAGE PATTERNS")
    print("=" * 80)

    print(f"\nTop 20 most-used nodes:")
    sorted_nodes = sorted(node_job_counts.items(), key=lambda x: x[1], reverse=True)
    for node, count in sorted_nodes[:20]:
        print(f"  {node}: {count:,} jobs")

    print(f"\nTop 20 least-used nodes:")
    for node, count in sorted_nodes[-20:]:
        print(f"  {node}: {count:,} jobs")

    # Temporal utilization
    print(f"\n" + "=" * 80)
    print("TEMPORAL UTILIZATION PATTERNS")
    print("=" * 80)

    # Bin by month
    df['month'] = df['start_time'].dt.to_period('M')
    monthly_cpu_hours = df.groupby('month')['cpu_hours'].sum()
    monthly_job_counts = df.groupby('month').size()

    print(f"\nMonthly CPU-hours and job counts:")
    for month in sorted(monthly_cpu_hours.index):
        cpu_hrs = monthly_cpu_hours[month]
        jobs = monthly_job_counts[month]

        # Calculate days in this month's data
        month_start = month.to_timestamp()
        month_end = (month + 1).to_timestamp()
        actual_start = max(month_start, start_date)
        actual_end = min(month_end, end_date)
        days_in_month = (actual_end - actual_start).total_seconds() / 86400

        month_theoretical = total_cpus * days_in_month * 24
        month_util = (cpu_hrs / month_theoretical) * 100 if month_theoretical > 0 else 0

        print(f"  {month}: {cpu_hrs:12,.0f} CPU-hrs, {jobs:8,} jobs, {month_util:5.2f}% util")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    csv_file = "/Users/scttfrdmn/src/cluster-job-analysis/oscar_all_jobs_2025.csv"
    analyze_cluster(csv_file)
