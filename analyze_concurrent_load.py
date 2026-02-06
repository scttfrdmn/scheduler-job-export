#!/usr/bin/env python3
"""
Analyze concurrent workload over time to understand:
1. Peak concurrent CPU usage
2. Average concurrent CPU usage
3. Temporal patterns in actual load
4. True cloud cost based on instantaneous usage
5. Peak-to-average ratio

This is critical for cloud cost comparison because M/M/∞ (cloud)
pays for instantaneous load, not total CPU-hours.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import sys

def analyze_concurrent_load(csv_file):
    """Analyze concurrent workload patterns over time"""

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
    df['run_time_seconds'] = (df['end_time'] - df['start_time']).dt.total_seconds()

    # Filter valid jobs
    df = df[(df['run_time_seconds'] > 0) & (df['run_time_seconds'] < 360000)]

    # Determine node type
    df['node_type'] = df['nodelist'].apply(lambda x: 'gpu' if 'gpu' in str(x).lower() else 'compute')

    print("=" * 80)
    print("TEMPORAL WORKLOAD ANALYSIS")
    print("=" * 80)

    # Get time range
    start_date = df['start_time'].min()
    end_date = df['end_time'].max()
    total_days = (end_date - start_date).total_seconds() / 86400

    print(f"\nTime period: {start_date} to {end_date}")
    print(f"Duration: {total_days:.1f} days")

    # Sample time points every hour
    print(f"\nSampling concurrent workload every hour...")

    time_points = []
    concurrent_cpus = []
    concurrent_compute_cpus = []
    concurrent_gpu_cpus = []
    concurrent_jobs = []

    # Create time points (every hour)
    current_time = start_date
    sample_interval = timedelta(hours=1)

    sample_count = 0
    while current_time <= end_date:
        # Find all jobs running at this time point
        running_jobs = df[(df['start_time'] <= current_time) & (df['end_time'] > current_time)]

        cpus = running_jobs['cpus_req'].sum()
        compute_cpus = running_jobs[running_jobs['node_type'] == 'compute']['cpus_req'].sum()
        gpu_cpus = running_jobs[running_jobs['node_type'] == 'gpu']['cpus_req'].sum()

        time_points.append(current_time)
        concurrent_cpus.append(cpus)
        concurrent_compute_cpus.append(compute_cpus)
        concurrent_gpu_cpus.append(gpu_cpus)
        concurrent_jobs.append(len(running_jobs))

        current_time += sample_interval
        sample_count += 1

        if sample_count % 1000 == 0:
            print(f"  Sampled {sample_count} time points ({current_time})...")

    print(f"Total time points sampled: {len(time_points):,}")

    # Convert to series for analysis
    concurrent_series = pd.Series(concurrent_cpus)
    compute_series = pd.Series(concurrent_compute_cpus)
    gpu_series = pd.Series(concurrent_gpu_cpus)
    jobs_series = pd.Series(concurrent_jobs)

    print("\n" + "=" * 80)
    print("CONCURRENT CPU USAGE STATISTICS")
    print("=" * 80)

    print(f"\nOverall Concurrent CPUs:")
    print(f"  Mean: {concurrent_series.mean():,.2f} CPUs")
    print(f"  Median: {concurrent_series.median():,.2f} CPUs")
    print(f"  Min: {concurrent_series.min():,.0f} CPUs")
    print(f"  Max: {concurrent_series.max():,.0f} CPUs")
    print(f"  Std Dev: {concurrent_series.std():,.2f} CPUs")
    print(f"  95th percentile: {concurrent_series.quantile(0.95):,.0f} CPUs")
    print(f"  99th percentile: {concurrent_series.quantile(0.99):,.0f} CPUs")

    print(f"\nConcurrent Compute CPUs:")
    print(f"  Mean: {compute_series.mean():,.2f} CPUs")
    print(f"  Median: {compute_series.median():,.2f} CPUs")
    print(f"  Max: {compute_series.max():,.0f} CPUs")
    print(f"  95th percentile: {compute_series.quantile(0.95):,.0f} CPUs")

    print(f"\nConcurrent GPU CPUs:")
    print(f"  Mean: {gpu_series.mean():,.2f} CPUs")
    print(f"  Median: {gpu_series.median():,.2f} CPUs")
    print(f"  Max: {gpu_series.max():,.0f} CPUs")
    print(f"  95th percentile: {gpu_series.quantile(0.95):,.0f} CPUs")

    print(f"\nConcurrent Jobs:")
    print(f"  Mean: {jobs_series.mean():,.2f} jobs")
    print(f"  Median: {jobs_series.median():,.2f} jobs")
    print(f"  Max: {jobs_series.max():,.0f} jobs")

    # Peak to average ratio
    peak_to_avg = concurrent_series.max() / concurrent_series.mean()
    print(f"\nPeak-to-Average Ratio: {peak_to_avg:.2f}x")

    # Capacity utilization
    TOTAL_CPUS = 76800
    avg_utilization = (concurrent_series.mean() / TOTAL_CPUS) * 100
    peak_utilization = (concurrent_series.max() / TOTAL_CPUS) * 100

    print(f"\nCapacity Analysis:")
    print(f"  OSCAR Total Capacity: {TOTAL_CPUS:,} CPUs")
    print(f"  Average Concurrent Usage: {concurrent_series.mean():,.0f} CPUs ({avg_utilization:.2f}%)")
    print(f"  Peak Concurrent Usage: {concurrent_series.max():,.0f} CPUs ({peak_utilization:.2f}%)")
    print(f"  Over-provisioning Factor: {TOTAL_CPUS / concurrent_series.mean():.2f}x")

    # Time at different load levels
    print("\n" + "=" * 80)
    print("TIME AT DIFFERENT LOAD LEVELS")
    print("=" * 80)

    load_buckets = [
        (0, 5000, "<5K CPUs"),
        (5000, 10000, "5K-10K CPUs"),
        (10000, 15000, "10K-15K CPUs"),
        (15000, 20000, "15K-20K CPUs"),
        (20000, 30000, "20K-30K CPUs"),
        (30000, 40000, "30K-40K CPUs"),
        (40000, 50000, "40K-50K CPUs"),
        (50000, 100000, ">50K CPUs"),
    ]

    print(f"\nLoad distribution (hourly samples):")
    for low, high, label in load_buckets:
        count = len(concurrent_series[(concurrent_series >= low) & (concurrent_series < high)])
        pct = (count / len(concurrent_series)) * 100
        if count > 0:
            print(f"  {label:15s}: {count:6,} hours ({pct:5.2f}%)")

    # Calculate actual cloud cost based on instantaneous usage
    print("\n" + "=" * 80)
    print("CLOUD COST CALCULATION (Instantaneous Usage)")
    print("=" * 80)

    # AWS pricing scenarios
    on_demand_price = 0.042  # $/vCPU-hr
    spot_avg_price = 0.020   # $/vCPU-hr (realistic average)
    spot_low_price = 0.012   # $/vCPU-hr (best case)

    # Calculate cost for each time point (1 hour intervals)
    # Sum of (CPUs at time t) × (1 hour) × (price per CPU-hour)
    total_cpu_hours_actual = concurrent_series.sum()  # Sum across all hourly samples

    # Annual projection
    hours_sampled = len(concurrent_series)
    hours_per_year = 8760

    # If we sampled full period, use actual; otherwise project
    if hours_sampled >= hours_per_year * 0.9:  # Have most of a year
        annual_cpu_hours = total_cpu_hours_actual
    else:
        # Project to full year
        annual_cpu_hours = total_cpu_hours_actual * (hours_per_year / hours_sampled)

    print(f"\nActual concurrent usage:")
    print(f"  Total CPU-hours (from sampling): {total_cpu_hours_actual:,.0f}")
    print(f"  Hours sampled: {hours_sampled:,}")
    print(f"  Annual projection: {annual_cpu_hours:,.0f} CPU-hours/year")

    # Compare to simple average calculation
    simple_calculation = concurrent_series.mean() * hours_per_year
    print(f"  Simple calculation (mean × 8760): {simple_calculation:,.0f} CPU-hours/year")
    print(f"  Difference: {abs(annual_cpu_hours - simple_calculation):,.0f} CPU-hours")

    # Cloud costs
    print(f"\nAnnual AWS costs (instantaneous usage):")
    print(f"  On-Demand (${on_demand_price}/vCPU-hr): ${annual_cpu_hours * on_demand_price:,.0f}")
    print(f"  Spot Average (${spot_avg_price}/vCPU-hr): ${annual_cpu_hours * spot_avg_price:,.0f}")
    print(f"  Spot Best (${spot_low_price}/vCPU-hr): ${annual_cpu_hours * spot_low_price:,.0f}")

    # OSCAR costs
    oscar_annual_cost = 9_000_000
    print(f"\nOSCAR annual cost (estimated): ${oscar_annual_cost:,}")

    # Savings
    spot_avg_cost = annual_cpu_hours * spot_avg_price
    savings = oscar_annual_cost - spot_avg_cost
    savings_pct = (savings / oscar_annual_cost) * 100

    print(f"\nSavings with AWS Spot:")
    print(f"  Absolute: ${savings:,.0f}/year")
    print(f"  Percentage: {savings_pct:.1f}%")

    # Cost per CPU-hour comparison
    oscar_cost_per_cpu_hr = oscar_annual_cost / annual_cpu_hours
    print(f"\nCost per CPU-hour comparison:")
    print(f"  OSCAR: ${oscar_cost_per_cpu_hr:.3f}/CPU-hr")
    print(f"  AWS On-Demand: ${on_demand_price:.3f}/CPU-hr")
    print(f"  AWS Spot Avg: ${spot_avg_price:.3f}/CPU-hr")
    print(f"  AWS Spot Best: ${spot_low_price:.3f}/CPU-hr")
    print(f"  OSCAR premium: {oscar_cost_per_cpu_hr / spot_avg_price:.1f}x vs Spot")

    # Analyze peak provisioning
    print("\n" + "=" * 80)
    print("PEAK PROVISIONING ANALYSIS")
    print("=" * 80)

    # What if OSCAR was sized for 95th percentile instead of 100%?
    p95_cpus = concurrent_series.quantile(0.95)
    p99_cpus = concurrent_series.quantile(0.99)

    print(f"\nAlternative sizing scenarios:")
    print(f"  Current capacity: {TOTAL_CPUS:,} CPUs (100% coverage)")
    print(f"  95th percentile: {p95_cpus:,.0f} CPUs (5% of time over)")
    print(f"  99th percentile: {p99_cpus:,.0f} CPUs (1% of time over)")
    print(f"  Mean usage: {concurrent_series.mean():,.0f} CPUs")

    # Cost if sized differently
    sizing_scenarios = [
        ("Current (76,800 CPUs)", TOTAL_CPUS, 9_000_000),
        ("99th percentile", p99_cpus, 9_000_000 * (p99_cpus / TOTAL_CPUS)),
        ("95th percentile", p95_cpus, 9_000_000 * (p95_cpus / TOTAL_CPUS)),
        ("Mean + 2σ", concurrent_series.mean() + 2*concurrent_series.std(),
         9_000_000 * ((concurrent_series.mean() + 2*concurrent_series.std()) / TOTAL_CPUS)),
    ]

    print(f"\nOn-prem cost at different sizing:")
    for name, cpus, cost in sizing_scenarios:
        if cpus <= TOTAL_CPUS:
            print(f"  {name:30s}: ${cost:>12,.0f}/year ({cpus:>8,.0f} CPUs)")

    # Cloud burst scenario
    print("\n" + "=" * 80)
    print("HYBRID SCENARIO: SIZE FOR 95th, BURST TO CLOUD")
    print("=" * 80)

    # Size on-prem for 95th percentile, burst rest to cloud
    onprem_capacity = p95_cpus
    burst_hours = concurrent_series[concurrent_series > onprem_capacity].sum() - (len(concurrent_series[concurrent_series > onprem_capacity]) * onprem_capacity)
    burst_annual = burst_hours * (hours_per_year / hours_sampled)

    onprem_cost = 9_000_000 * (onprem_capacity / TOTAL_CPUS)
    burst_cost = burst_annual * spot_avg_price

    print(f"\nHybrid approach:")
    print(f"  On-prem capacity: {onprem_capacity:,.0f} CPUs (95th percentile)")
    print(f"  On-prem cost: ${onprem_cost:,.0f}/year")
    print(f"  Burst CPU-hours: {burst_annual:,.0f}/year")
    print(f"  Burst cost (AWS Spot): ${burst_cost:,.0f}/year")
    print(f"  Total hybrid cost: ${onprem_cost + burst_cost:,.0f}/year")
    print(f"  Savings vs current: ${oscar_annual_cost - (onprem_cost + burst_cost):,.0f}/year")
    print(f"  Savings percentage: {((oscar_annual_cost - (onprem_cost + burst_cost)) / oscar_annual_cost) * 100:.1f}%")

    # Temporal patterns
    print("\n" + "=" * 80)
    print("TEMPORAL PATTERNS IN CONCURRENT LOAD")
    print("=" * 80)

    # Create dataframe for temporal analysis
    temporal_df = pd.DataFrame({
        'time': time_points,
        'cpus': concurrent_cpus,
        'jobs': concurrent_jobs
    })
    temporal_df['hour'] = temporal_df['time'].dt.hour
    temporal_df['day_of_week'] = temporal_df['time'].dt.dayofweek

    # By hour of day
    print(f"\nAverage concurrent CPUs by hour of day:")
    hourly_avg = temporal_df.groupby('hour')['cpus'].mean()
    for hour in range(24):
        if hour in hourly_avg.index:
            cpus = hourly_avg[hour]
            print(f"  {hour:02d}:00 - {cpus:>8,.0f} CPUs")

    # By day of week
    print(f"\nAverage concurrent CPUs by day of week:")
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_avg = temporal_df.groupby('day_of_week')['cpus'].mean()
    for day in range(7):
        if day in daily_avg.index:
            cpus = daily_avg[day]
            print(f"  {day_names[day]:9s} - {cpus:>8,.0f} CPUs")

    # Busiest times
    print(f"\nBusiest time periods (top 20):")
    busiest = temporal_df.nlargest(20, 'cpus')
    for idx, row in busiest.iterrows():
        print(f"  {row['time']}: {row['cpus']:>6,.0f} CPUs, {row['jobs']:>5,.0f} jobs")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    # Summary
    print(f"\n*** KEY FINDINGS ***")
    print(f"\n1. OSCAR is provisioned for {TOTAL_CPUS:,} CPUs but:")
    print(f"   - Average concurrent usage: {concurrent_series.mean():,.0f} CPUs ({avg_utilization:.2f}%)")
    print(f"   - Peak concurrent usage: {concurrent_series.max():,.0f} CPUs ({peak_utilization:.2f}%)")
    print(f"   - Over-provisioned by: {TOTAL_CPUS / concurrent_series.mean():.1f}x")

    print(f"\n2. Cloud (M/M/∞) cost based on ACTUAL concurrent load:")
    print(f"   - Annual CPU-hours: {annual_cpu_hours:,.0f}")
    print(f"   - Cost at AWS Spot prices: ${annual_cpu_hours * spot_avg_price:,.0f}/year")
    print(f"   - Savings vs OSCAR: ${savings:,.0f}/year ({savings_pct:.1f}%)")

    print(f"\n3. Peak-to-average ratio: {peak_to_avg:.2f}x")
    print(f"   - Cloud handles this perfectly (M/M/∞)")
    print(f"   - On-prem must provision for peak")

    print(f"\n4. Better on-prem sizing:")
    print(f"   - Size for 95th percentile: {p95_cpus:,.0f} CPUs")
    print(f"   - Would save: ${oscar_annual_cost - (9_000_000 * (p95_cpus / TOTAL_CPUS)):,.0f}/year")
    print(f"   - Still cover 95% of demand")

if __name__ == "__main__":
    csv_file = "/Users/scttfrdmn/src/cluster-job-analysis/oscar_all_jobs_2025.csv"
    analyze_concurrent_load(csv_file)
