#!/usr/bin/env python3
"""
Analyze HPC cluster job records from OSCAR cluster
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

# Constants
MAX_INT_64 = 9223372036854775807
SUSPICIOUS_MEM_THRESHOLD = 9223372036854000000  # Close to MAX_INT

def parse_timestamps(df):
    """Parse timestamp columns"""
    df['submit_time'] = pd.to_datetime(df['submit_time'])
    df['start_time'] = pd.to_datetime(df['start_time'])
    df['end_time'] = pd.to_datetime(df['end_time'])
    return df

def calculate_durations(df):
    """Calculate job durations"""
    df['queue_time'] = (df['start_time'] - df['submit_time']).dt.total_seconds() / 60  # minutes
    df['run_time'] = (df['end_time'] - df['start_time']).dt.total_seconds() / 60  # minutes
    return df

def analyze_jobs(csv_file):
    """Analyze job patterns and statistics"""

    print("Loading data (this may take a moment for 692MB file)...")
    print("=" * 80)

    # Read CSV in chunks to handle large file
    chunk_size = 100000
    chunks = []
    total_rows = 0

    for chunk in pd.read_csv(csv_file, chunksize=chunk_size):
        chunks.append(chunk)
        total_rows += len(chunk)
        if len(chunks) % 10 == 0:
            print(f"Loaded {total_rows:,} rows...")

    df = pd.concat(chunks, ignore_index=True)
    print(f"Total rows loaded: {len(df):,}\n")

    # Parse timestamps and calculate durations
    df = parse_timestamps(df)
    df = calculate_durations(df)

    # Basic statistics
    print("=" * 80)
    print("BASIC STATISTICS")
    print("=" * 80)
    print(f"Total jobs: {len(df):,}")
    print(f"Date range: {df['submit_time'].min()} to {df['end_time'].max()}")
    print(f"Time span: {(df['end_time'].max() - df['submit_time'].min()).days} days\n")

    # Memory analysis - check for MAX_INT
    print("=" * 80)
    print("MEMORY REQUEST ANALYSIS")
    print("=" * 80)
    max_int_jobs = df[df['mem_req'] >= SUSPICIOUS_MEM_THRESHOLD]
    print(f"Jobs with mem_req >= {SUSPICIOUS_MEM_THRESHOLD:,}: {len(max_int_jobs):,} ({len(max_int_jobs)/len(df)*100:.2f}%)")
    print(f"Unique 'suspicious' mem_req values: {df[df['mem_req'] >= SUSPICIOUS_MEM_THRESHOLD]['mem_req'].unique()}")
    print(f"\nActual MAX_INT64: {MAX_INT_64:,}")
    print(f"Values in dataset near MAX_INT: {sorted(df[df['mem_req'] >= SUSPICIOUS_MEM_THRESHOLD]['mem_req'].unique())}")

    # Memory stats for normal jobs
    normal_mem = df[df['mem_req'] < SUSPICIOUS_MEM_THRESHOLD]['mem_req']
    print(f"\nMemory statistics (excluding MAX_INT-like values):")
    print(f"  Mean: {normal_mem.mean()/1024:.2f} GB")
    print(f"  Median: {normal_mem.median()/1024:.2f} GB")
    print(f"  Min: {normal_mem.min()/1024:.2f} GB")
    print(f"  Max: {normal_mem.max()/1024:.2f} GB")
    print(f"  Std: {normal_mem.std()/1024:.2f} GB\n")

    # CPU analysis
    print("=" * 80)
    print("CPU REQUEST ANALYSIS")
    print("=" * 80)
    print(f"CPU statistics:")
    print(f"  Mean: {df['cpus_req'].mean():.2f}")
    print(f"  Median: {df['cpus_req'].median():.0f}")
    print(f"  Min: {df['cpus_req'].min()}")
    print(f"  Max: {df['cpus_req'].max()}")
    print(f"  Std: {df['cpus_req'].std():.2f}")

    print(f"\nTop CPU request sizes (top 10):")
    cpu_counts = df['cpus_req'].value_counts().head(10)
    for cpus, count in cpu_counts.items():
        print(f"  {cpus:4d} CPUs: {count:8,} jobs ({count/len(df)*100:5.2f}%)")

    # Node analysis
    print("\n" + "=" * 80)
    print("NODE ALLOCATION ANALYSIS")
    print("=" * 80)
    print(f"Node allocation statistics:")
    print(f"  Mean: {df['nodes_alloc'].mean():.2f}")
    print(f"  Median: {df['nodes_alloc'].median():.0f}")
    print(f"  Min: {df['nodes_alloc'].min()}")
    print(f"  Max: {df['nodes_alloc'].max()}")

    node_counts = df['nodes_alloc'].value_counts().head(10)
    print(f"\nTop node allocation sizes (top 10):")
    for nodes, count in node_counts.items():
        print(f"  {nodes:4d} nodes: {count:8,} jobs ({count/len(df)*100:5.2f}%)")

    # GPU jobs detection
    print("\n" + "=" * 80)
    print("GPU JOB ANALYSIS")
    print("=" * 80)
    gpu_jobs = df[df['nodelist'].str.contains('gpu', case=False, na=False)]
    print(f"Jobs on GPU nodes: {len(gpu_jobs):,} ({len(gpu_jobs)/len(df)*100:.2f}%)")

    if len(gpu_jobs) > 0:
        print(f"\nGPU node distribution:")
        gpu_node_counts = gpu_jobs['nodelist'].value_counts().head(10)
        for node, count in gpu_node_counts.items():
            print(f"  {node}: {count:,} jobs")

    # Duration analysis
    print("\n" + "=" * 80)
    print("JOB DURATION ANALYSIS")
    print("=" * 80)

    # Filter out negative or extreme values
    valid_queue = df[(df['queue_time'] >= 0) & (df['queue_time'] < 10000000)]
    valid_run = df[(df['run_time'] >= 0) & (df['run_time'] < 10000000)]

    print(f"Queue time (wait time) statistics:")
    print(f"  Mean: {valid_queue['queue_time'].mean()/60:.2f} hours")
    print(f"  Median: {valid_queue['queue_time'].median()/60:.2f} hours")
    print(f"  Max: {valid_queue['queue_time'].max()/60:.2f} hours")

    print(f"\nRun time statistics:")
    print(f"  Mean: {valid_run['run_time'].mean()/60:.2f} hours")
    print(f"  Median: {valid_run['run_time'].median()/60:.2f} hours")
    print(f"  Max: {valid_run['run_time'].max()/60:.2f} hours")

    # Short vs long jobs
    short_jobs = df[df['run_time'] < 60]  # < 1 hour
    long_jobs = df[df['run_time'] > 24*60]  # > 24 hours
    print(f"\nJob duration categories:")
    print(f"  Short jobs (< 1 hour): {len(short_jobs):,} ({len(short_jobs)/len(df)*100:.2f}%)")
    print(f"  Long jobs (> 24 hours): {len(long_jobs):,} ({len(long_jobs)/len(df)*100:.2f}%)")

    # Time patterns
    print("\n" + "=" * 80)
    print("TEMPORAL PATTERNS")
    print("=" * 80)

    df['submit_hour'] = df['submit_time'].dt.hour
    df['submit_dow'] = df['submit_time'].dt.dayofweek  # 0=Monday

    print(f"\nPeak submission hours (top 5):")
    hour_counts = df['submit_hour'].value_counts().head(5)
    for hour, count in hour_counts.items():
        print(f"  {hour:02d}:00: {count:,} jobs ({count/len(df)*100:.2f}%)")

    print(f"\nSubmissions by day of week:")
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_counts = df['submit_dow'].value_counts().sort_index()
    for dow, count in dow_counts.items():
        print(f"  {day_names[dow]:9s}: {count:8,} jobs ({count/len(df)*100:5.2f}%)")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    csv_file = "/Users/scttfrdmn/src/cluster-job-analysis/oscar_all_jobs_2025.csv"
    analyze_jobs(csv_file)
