#!/usr/bin/env python3
"""
Analyze cluster utilization patterns: throughput vs capacity, job packing, provisioning
"""

import pandas as pd
import numpy as np
import re
from collections import defaultdict
from datetime import datetime, timedelta

# Constants from previous analysis
GPU_CPUS = 128
NODE_CPUS = 192
TOTAL_GPU_NODES = 105
TOTAL_COMPUTE_NODES = 330
TOTAL_CPUS = (GPU_CPUS * TOTAL_GPU_NODES) + (NODE_CPUS * TOTAL_COMPUTE_NODES)
MAX_INT_THRESHOLD = 9223372036854000000

def expand_nodelist(nodelist_str):
    """Expand SLURM nodelist format"""
    if pd.isna(nodelist_str) or nodelist_str == '':
        return []

    nodes = []
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
        nodes.append(nodelist_str)

    return nodes

def analyze_packing(csv_file):
    """Analyze job packing and cluster configuration patterns"""

    print("Loading job data...")
    print("=" * 80)

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

    # Filter valid jobs
    df = df[(df['run_time'] >= 0) & (df['run_time'] < 100000)]

    # Determine node type
    df['node_type'] = df['nodelist'].apply(lambda x: 'gpu' if 'gpu' in str(x).lower() else 'node')
    df['node_cpus'] = df['node_type'].map({'gpu': GPU_CPUS, 'node': NODE_CPUS})

    print("=" * 80)
    print("CORE UTILIZATION ANALYSIS")
    print("=" * 80)

    # For single-node jobs, calculate what % of node cores were used
    single_node = df[df['nodes_alloc'] == 1].copy()
    single_node['core_utilization'] = (single_node['cpus_req'] / single_node['node_cpus']) * 100

    print(f"\nSingle-node job core utilization:")
    print(f"  Mean: {single_node['core_utilization'].mean():.2f}%")
    print(f"  Median: {single_node['core_utilization'].median():.2f}%")
    print(f"  Jobs using <10% of cores: {len(single_node[single_node['core_utilization'] < 10]):,} ({len(single_node[single_node['core_utilization'] < 10])/len(single_node)*100:.2f}%)")
    print(f"  Jobs using 10-50% of cores: {len(single_node[(single_node['core_utilization'] >= 10) & (single_node['core_utilization'] < 50)]):,} ({len(single_node[(single_node['core_utilization'] >= 10) & (single_node['core_utilization'] < 50)])/len(single_node)*100:.2f}%)")
    print(f"  Jobs using 50-90% of cores: {len(single_node[(single_node['core_utilization'] >= 50) & (single_node['core_utilization'] < 90)]):,} ({len(single_node[(single_node['core_utilization'] >= 50) & (single_node['core_utilization'] < 90)])/len(single_node)*100:.2f}%)")
    print(f"  Jobs using >90% of cores: {len(single_node[single_node['core_utilization'] > 90]):,} ({len(single_node[single_node['core_utilization'] > 90])/len(single_node)*100:.2f}%)")

    # Full node allocations
    full_node_gpu = single_node[(single_node['node_type'] == 'gpu') & (single_node['cpus_req'] >= GPU_CPUS)]
    full_node_compute = single_node[(single_node['node_type'] == 'node') & (single_node['cpus_req'] >= NODE_CPUS)]

    print(f"\nFull-node allocations:")
    print(f"  GPU nodes fully allocated: {len(full_node_gpu):,} ({len(full_node_gpu)/len(single_node[single_node['node_type']=='gpu'])*100:.2f}% of GPU jobs)")
    print(f"  Compute nodes fully allocated: {len(full_node_compute):,} ({len(full_node_compute)/len(single_node[single_node['node_type']=='node'])*100:.2f}% of compute jobs)")

    print("\n" + "=" * 80)
    print("MEMORY UTILIZATION ANALYSIS")
    print("=" * 80)

    # Memory analysis
    normal_mem_jobs = single_node[single_node['mem_req'] < MAX_INT_THRESHOLD].copy()

    # Estimate node memory (typical HPC configs)
    # GPU nodes often have more memory, compute nodes vary
    # Based on mem_req distribution, estimate available memory
    gpu_jobs = normal_mem_jobs[normal_mem_jobs['node_type'] == 'gpu']
    compute_jobs = normal_mem_jobs[normal_mem_jobs['node_type'] == 'node']

    print(f"\nMemory request statistics (excluding MAX_INT values):")

    print(f"\nGPU nodes:")
    if len(gpu_jobs) > 0:
        print(f"  Max memory requested: {gpu_jobs['mem_req'].max()/1024:.2f} GB")
        print(f"  95th percentile: {gpu_jobs['mem_req'].quantile(0.95)/1024:.2f} GB")
        print(f"  75th percentile: {gpu_jobs['mem_req'].quantile(0.75)/1024:.2f} GB")
        print(f"  Median: {gpu_jobs['mem_req'].median()/1024:.2f} GB")
        print(f"  Mean: {gpu_jobs['mem_req'].mean()/1024:.2f} GB")

        # Estimate node memory (probably 256 GB, 512 GB, or 1 TB for GPU nodes)
        likely_gpu_mem = 512  # GB - common for GPU nodes
        gpu_jobs['mem_utilization'] = (gpu_jobs['mem_req'] / 1024 / likely_gpu_mem) * 100
        print(f"  Estimated node memory: ~{likely_gpu_mem} GB")
        print(f"  Mean memory utilization: {gpu_jobs['mem_utilization'].mean():.2f}%")

    print(f"\nCompute nodes:")
    if len(compute_jobs) > 0:
        print(f"  Max memory requested: {compute_jobs['mem_req'].max()/1024:.2f} GB")
        print(f"  95th percentile: {compute_jobs['mem_req'].quantile(0.95)/1024:.2f} GB")
        print(f"  75th percentile: {compute_jobs['mem_req'].quantile(0.75)/1024:.2f} GB")
        print(f"  Median: {compute_jobs['mem_req'].median()/1024:.2f} GB")
        print(f"  Mean: {compute_jobs['mem_req'].mean()/1024:.2f} GB")

        # Estimate node memory (probably 256 GB or 512 GB for compute nodes)
        likely_compute_mem = 256  # GB - common for compute nodes
        compute_jobs['mem_utilization'] = (compute_jobs['mem_req'] / 1024 / likely_compute_mem) * 100
        print(f"  Estimated node memory: ~{likely_compute_mem} GB")
        print(f"  Mean memory utilization: {compute_jobs['mem_utilization'].mean():.2f}%")

    print("\n" + "=" * 80)
    print("JOB PACKING ANALYSIS")
    print("=" * 80)

    # Analyze potential for job packing
    # Small jobs that could share nodes
    small_cpu_jobs = single_node[single_node['cpus_req'] <= 4]
    small_short_jobs = small_cpu_jobs[small_cpu_jobs['run_time'] < 1]  # < 1 hour

    print(f"\nSmall job characteristics (≤4 CPUs):")
    print(f"  Total small CPU jobs: {len(small_cpu_jobs):,} ({len(small_cpu_jobs)/len(single_node)*100:.2f}% of single-node jobs)")
    print(f"  Small + short (<1hr): {len(small_short_jobs):,} ({len(small_short_jobs)/len(single_node)*100:.2f}% of single-node jobs)")

    # Calculate average cores wasted
    single_node['cores_wasted'] = single_node['node_cpus'] - single_node['cpus_req']
    total_cores_wasted = (single_node['cores_wasted'] * single_node['run_time']).sum()
    total_node_hours = (single_node['nodes_alloc'] * single_node['run_time']).sum()
    avg_cores_wasted_per_node = single_node['cores_wasted'].mean()

    print(f"\nCore waste analysis (single-node jobs):")
    print(f"  Average cores unused per job: {avg_cores_wasted_per_node:.2f}")
    print(f"  Total core-hours wasted: {total_cores_wasted:,.0f}")
    print(f"  % of node capacity wasted: {(total_cores_wasted / (total_node_hours * NODE_CPUS)) * 100:.2f}%")

    print("\n" + "=" * 80)
    print("THROUGHPUT vs CAPACITY ANALYSIS")
    print("=" * 80)

    # Throughput characteristics:
    # - Many small jobs
    # - Fast turnaround
    # - Lower utilization
    # - Jobs don't wait long
    # - Emphasis on job count over resource usage

    # Capacity characteristics:
    # - Larger jobs
    # - High utilization
    # - Jobs packed efficiently
    # - May have longer queues
    # - Emphasis on maximizing resource usage

    df['queue_time'] = (df['start_time'] - df['submit_time']).dt.total_seconds() / 60  # minutes
    valid_queue = df[(df['queue_time'] >= 0) & (df['queue_time'] < 1000000)]

    print(f"\nCluster characteristics:")
    print(f"  Median queue time: {valid_queue['queue_time'].median():.2f} minutes")
    print(f"  % jobs starting in <5 min: {len(valid_queue[valid_queue['queue_time'] < 5])/len(valid_queue)*100:.2f}%")
    print(f"  % jobs starting in <30 min: {len(valid_queue[valid_queue['queue_time'] < 30])/len(valid_queue)*100:.2f}%")
    print(f"  % single-core jobs: {len(df[df['cpus_req'] == 1])/len(df)*100:.2f}%")
    print(f"  % jobs using ≤4 cores: {len(df[df['cpus_req'] <= 4])/len(df)*100:.2f}%")
    print(f"  % jobs running <1 hour: {len(df[df['run_time'] < 1])/len(df)*100:.2f}%")
    print(f"  Average CPU utilization: 12.79%")
    print(f"  Average cores per job: {df['cpus_req'].mean():.2f}")

    throughput_score = 0
    capacity_score = 0

    # Score based on characteristics
    if valid_queue['queue_time'].median() < 5:
        throughput_score += 2
    if len(df[df['cpus_req'] == 1])/len(df) > 0.5:
        throughput_score += 2
    if len(df[df['run_time'] < 1])/len(df) > 0.7:
        throughput_score += 2
    if 12.79 < 20:  # Low utilization
        throughput_score += 1

    if valid_queue['queue_time'].median() > 30:
        capacity_score += 2
    if df['cpus_req'].mean() > 10:
        capacity_score += 2
    if 12.79 > 70:  # High utilization
        capacity_score += 2

    print(f"\n*** CLUSTER TYPE ASSESSMENT ***")
    print(f"Throughput indicators: {throughput_score}/7")
    print(f"Capacity indicators: {capacity_score}/6")

    if throughput_score > capacity_score:
        print(f"\nConclusion: This is a THROUGHPUT COMPUTING cluster")
        print(f"  - Optimized for job count and fast turnaround")
        print(f"  - NOT optimized for resource utilization")
        print(f"  - Users expect quick job starts over high efficiency")
    else:
        print(f"\nConclusion: This is a CAPACITY COMPUTING cluster")
        print(f"  - Optimized for resource utilization")
        print(f"  - Jobs may wait longer for optimal packing")

    print("\n" + "=" * 80)
    print("PROVISIONING ASSESSMENT")
    print("=" * 80)

    # Assess if cluster is over/under provisioned
    utilization = 12.79
    median_queue = valid_queue['queue_time'].median()

    print(f"\nKey metrics:")
    print(f"  CPU utilization: {utilization:.2f}%")
    print(f"  Median queue time: {median_queue:.2f} minutes")
    print(f"  Total nodes: {TOTAL_GPU_NODES + TOTAL_COMPUTE_NODES}")
    print(f"  Total CPUs: {TOTAL_CPUS:,}")

    print(f"\n*** PROVISIONING ANALYSIS ***")

    if utilization < 20 and median_queue < 5:
        print(f"\nStatus: SIGNIFICANTLY OVER-PROVISIONED")
        print(f"  - Very low utilization ({utilization:.1f}%)")
        print(f"  - Extremely short queue times ({median_queue:.1f} min)")
        print(f"  - Users rarely wait for resources")
        print(f"\nRecommendations:")
        print(f"  - Cluster could operate with 30-40% fewer nodes")
        print(f"  - Could consolidate {int((TOTAL_GPU_NODES + TOTAL_COMPUTE_NODES) * 0.3)} nodes")
        print(f"  - Target utilization: 40-60% for throughput, 70-85% for capacity")
        print(f"  - Consider implementing job packing/sharing for small jobs")
        print(f"  - Could save significant operational costs")

    elif utilization < 30 and median_queue < 10:
        print(f"\nStatus: MODERATELY OVER-PROVISIONED")
        print(f"  - Low utilization ({utilization:.1f}%)")
        print(f"  - Short queue times ({median_queue:.1f} min)")
        print(f"\nRecommendations:")
        print(f"  - Slight over-provisioning may be acceptable for throughput model")
        print(f"  - Consider 10-20% reduction in nodes")
        print(f"  - Improve job packing for better efficiency")

    elif utilization > 70 and median_queue > 60:
        print(f"\nStatus: UNDER-PROVISIONED")
        print(f"  - High utilization ({utilization:.1f}%)")
        print(f"  - Long queue times ({median_queue:.1f} min)")
        print(f"\nRecommendations:")
        print(f"  - Consider adding nodes")
        print(f"  - Or improve job scheduling/packing")

    else:
        print(f"\nStatus: APPROPRIATELY PROVISIONED")
        print(f"  - Balanced utilization and queue times")

    # Potential savings calculation
    if utilization < 20:
        potential_reduction = 1 - (20 / utilization)
        nodes_to_remove = int((TOTAL_GPU_NODES + TOTAL_COMPUTE_NODES) * potential_reduction)
        cpus_to_remove = int(TOTAL_CPUS * potential_reduction)

        print(f"\nPotential optimization:")
        print(f"  Could remove up to {nodes_to_remove} nodes ({potential_reduction*100:.1f}%)")
        print(f"  Would free up {cpus_to_remove:,} CPUs")
        print(f"  Would increase utilization to ~20-25%")
        print(f"  Would maintain queue times under 10 minutes")
        print(f"  Estimated cost savings: {potential_reduction*100:.1f}% of compute infrastructure")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    csv_file = "/Users/scttfrdmn/src/cluster-job-analysis/oscar_all_jobs_2025.csv"
    analyze_packing(csv_file)
