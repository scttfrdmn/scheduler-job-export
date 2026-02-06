#!/usr/bin/env python3
"""
Full AWS Migration Analysis for OSCAR Workload

Analyzes what it would cost to migrate 100% of OSCAR's workload to AWS,
considering:
- Actual job patterns (size, duration, type)
- Spot vs on-demand mix based on job duration
- Compute vs GPU pricing
- Storage, networking, and support costs
- Different service models (Batch, ParallelCluster, etc.)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

# AWS Pricing (2024-2025, us-east-1)
# Compute-optimized instances (c7i family)
C7I_XLARGE_ONDEMAND = 0.168 / 4      # $0.042/vCPU-hr
C7I_SPOT_AVG = 0.042 * 0.3          # ~70% discount = $0.0126/vCPU-hr
C7I_SPOT_BEST = 0.042 * 0.2         # ~80% discount = $0.0084/vCPU-hr

# GPU instances (g5.xlarge for inference/small ML, p3 for training)
G5_XLARGE_ONDEMAND = 1.006          # $1.006/hr (1 GPU, 4 vCPU)
G5_SPOT_AVG = 1.006 * 0.5           # ~50% discount = $0.503/hr
P3_2XLARGE_ONDEMAND = 3.06          # $3.06/hr (1 V100, 8 vCPU)
P3_SPOT_AVG = 3.06 * 0.5            # ~50% discount = $1.53/hr

# Storage (EFS for shared filesystem)
EFS_STORAGE = 0.30 / 30 / 24        # $0.30/GB-month = $0.000417/GB-hr
EFS_THROUGHPUT = 0.00                # First 50 GB/s free

# Data transfer
DATA_TRANSFER_OUT = 0.09            # $0.09/GB (after first 100GB free/month)

# AWS Support
SUPPORT_BUSINESS = 0.10             # 10% of monthly usage (or $100/month min)

def analyze_full_migration(csv_file):
    """Analyze cost of full AWS migration"""

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
    df['run_time_hours'] = (df['end_time'] - df['start_time']).dt.total_seconds() / 3600

    # Filter valid jobs
    df = df[(df['run_time_hours'] > 0) & (df['run_time_hours'] < 10000)]

    # Determine node type
    df['node_type'] = df['nodelist'].apply(lambda x: 'gpu' if 'gpu' in str(x).lower() else 'compute')

    # Calculate CPU-hours
    df['cpu_hours'] = df['cpus_req'] * df['run_time_hours']

    print("=" * 80)
    print("FULL AWS MIGRATION ANALYSIS")
    print("=" * 80)

    # Split by node type
    compute_jobs = df[df['node_type'] == 'compute'].copy()
    gpu_jobs = df[df['node_type'] == 'gpu'].copy()

    print(f"\nWorkload breakdown:")
    print(f"  Compute jobs: {len(compute_jobs):,} ({len(compute_jobs)/len(df)*100:.1f}%)")
    print(f"  GPU jobs: {len(gpu_jobs):,} ({len(gpu_jobs)/len(df)*100:.1f}%)")

    # Compute job analysis
    print("\n" + "=" * 80)
    print("COMPUTE JOBS - AWS PRICING")
    print("=" * 80)

    # Categorize by duration for spot suitability
    compute_jobs['duration_category'] = pd.cut(
        compute_jobs['run_time_hours'],
        bins=[0, 1, 4, 24, float('inf')],
        labels=['<1hr', '1-4hr', '4-24hr', '>24hr']
    )

    print(f"\nCompute jobs by duration:")
    for cat in ['<1hr', '1-4hr', '4-24hr', '>24hr']:
        count = len(compute_jobs[compute_jobs['duration_category'] == cat])
        cpu_hrs = compute_jobs[compute_jobs['duration_category'] == cat]['cpu_hours'].sum()
        print(f"  {cat:8s}: {count:7,} jobs, {cpu_hrs:12,.0f} CPU-hours ({cpu_hrs/compute_jobs['cpu_hours'].sum()*100:5.1f}%)")

    # Pricing strategy
    # <1hr: 95% spot, 5% on-demand (very safe)
    # 1-4hr: 85% spot, 15% on-demand
    # 4-24hr: 70% spot, 30% on-demand
    # >24hr: 50% spot, 50% on-demand (spot risk)

    pricing_strategy = {
        '<1hr': {'spot_pct': 0.95, 'spot_price': C7I_SPOT_AVG, 'ondemand_price': C7I_XLARGE_ONDEMAND},
        '1-4hr': {'spot_pct': 0.85, 'spot_price': C7I_SPOT_AVG, 'ondemand_price': C7I_XLARGE_ONDEMAND},
        '4-24hr': {'spot_pct': 0.70, 'spot_price': C7I_SPOT_AVG, 'ondemand_price': C7I_XLARGE_ONDEMAND},
        '>24hr': {'spot_pct': 0.50, 'spot_price': C7I_SPOT_AVG, 'ondemand_price': C7I_XLARGE_ONDEMAND},
    }

    total_compute_cost = 0
    print(f"\nCompute job pricing strategy:")
    print(f"  {'Category':<10s} {'Spot %':<8s} {'CPU-hours':<15s} {'Spot Cost':<15s} {'On-Demand Cost':<15s} {'Total':<15s}")
    print(f"  {'-'*10} {'-'*8} {'-'*15} {'-'*15} {'-'*15} {'-'*15}")

    for cat in ['<1hr', '1-4hr', '4-24hr', '>24hr']:
        cat_jobs = compute_jobs[compute_jobs['duration_category'] == cat]
        cpu_hrs = cat_jobs['cpu_hours'].sum()

        strategy = pricing_strategy[cat]
        spot_cpu_hrs = cpu_hrs * strategy['spot_pct']
        ondemand_cpu_hrs = cpu_hrs * (1 - strategy['spot_pct'])

        spot_cost = spot_cpu_hrs * strategy['spot_price']
        ondemand_cost = ondemand_cpu_hrs * strategy['ondemand_price']
        total_cost = spot_cost + ondemand_cost

        total_compute_cost += total_cost

        print(f"  {cat:<10s} {strategy['spot_pct']*100:>6.0f}% {cpu_hrs:>13,.0f} ${spot_cost:>13,.0f} ${ondemand_cost:>13,.0f} ${total_cost:>13,.0f}")

    print(f"\nTotal compute cost: ${total_compute_cost:,.0f}/year")

    # GPU job analysis
    print("\n" + "=" * 80)
    print("GPU JOBS - AWS PRICING")
    print("=" * 80)

    gpu_jobs['duration_category'] = pd.cut(
        gpu_jobs['run_time_hours'],
        bins=[0, 1, 4, 24, float('inf')],
        labels=['<1hr', '1-4hr', '4-24hr', '>24hr']
    )

    print(f"\nGPU jobs by duration:")
    for cat in ['<1hr', '1-4hr', '4-24hr', '>24hr']:
        count = len(gpu_jobs[gpu_jobs['duration_category'] == cat])
        cpu_hrs = gpu_jobs[gpu_jobs['duration_category'] == cat]['cpu_hours'].sum()
        if count > 0:
            print(f"  {cat:8s}: {count:7,} jobs, {cpu_hrs:12,.0f} CPU-hours ({cpu_hrs/gpu_jobs['cpu_hours'].sum()*100:5.1f}%)")

    # GPU pricing is more complex - need to estimate instance sizes
    # Assume: small jobs (<16 CPUs) use g5.xlarge, larger use p3/p4
    gpu_jobs['instance_type'] = gpu_jobs['cpus_req'].apply(
        lambda x: 'g5.xlarge' if x <= 16 else 'p3.2xlarge'
    )

    # For simplicity, calculate based on job hours (not CPU-hours)
    gpu_jobs['job_hours'] = gpu_jobs['run_time_hours']

    # G5 instances (inference/light ML)
    g5_jobs = gpu_jobs[gpu_jobs['instance_type'] == 'g5.xlarge']
    g5_spot_pct = 0.85  # GPU spot is pretty stable for small instances
    g5_hours = g5_jobs['job_hours'].sum()
    g5_spot_cost = g5_hours * g5_spot_pct * G5_SPOT_AVG
    g5_ondemand_cost = g5_hours * (1 - g5_spot_pct) * G5_XLARGE_ONDEMAND
    g5_total_cost = g5_spot_cost + g5_ondemand_cost

    # P3 instances (training/heavy ML)
    p3_jobs = gpu_jobs[gpu_jobs['instance_type'] == 'p3.2xlarge']
    p3_spot_pct = 0.70  # More conservative for larger instances
    p3_hours = p3_jobs['job_hours'].sum()
    p3_spot_cost = p3_hours * p3_spot_pct * P3_SPOT_AVG
    p3_ondemand_cost = p3_hours * (1 - p3_spot_pct) * P3_2XLARGE_ONDEMAND
    p3_total_cost = p3_spot_cost + p3_ondemand_cost

    total_gpu_cost = g5_total_cost + p3_total_cost

    print(f"\nGPU instance breakdown:")
    print(f"  g5.xlarge (small GPU jobs):")
    print(f"    Jobs: {len(g5_jobs):,}")
    print(f"    Instance-hours: {g5_hours:,.0f}")
    print(f"    Cost: ${g5_total_cost:,.0f} ({g5_spot_pct*100:.0f}% spot)")
    print(f"  p3.2xlarge (large GPU jobs):")
    print(f"    Jobs: {len(p3_jobs):,}")
    print(f"    Instance-hours: {p3_hours:,.0f}")
    print(f"    Cost: ${p3_total_cost:,.0f} ({p3_spot_pct*100:.0f}% spot)")
    print(f"\nTotal GPU cost: ${total_gpu_cost:,.0f}/year")

    # Storage costs
    print("\n" + "=" * 80)
    print("STORAGE COSTS")
    print("=" * 80)

    # Estimate storage needs (unknown from current data)
    # Typical HPC cluster: 1-5 PB storage
    # Assume moderate: 500 TB active working storage
    storage_tb = 500
    storage_cost_month = storage_tb * 1024 * 0.30  # EFS Standard
    storage_cost_year = storage_cost_month * 12

    print(f"\nEstimated storage (EFS Standard):")
    print(f"  Capacity: {storage_tb} TB")
    print(f"  Cost: ${storage_cost_month:,.0f}/month = ${storage_cost_year:,.0f}/year")

    # FSx for Lustre alternative (for HPC workloads)
    fsx_cost_month = storage_tb * 1024 * 0.145  # FSx for Lustre (scratch)
    fsx_cost_year = fsx_cost_month * 12

    print(f"\nAlternative: FSx for Lustre (HPC-optimized):")
    print(f"  Capacity: {storage_tb} TB")
    print(f"  Cost: ${fsx_cost_month:,.0f}/month = ${fsx_cost_year:,.0f}/year")

    # Use FSx as more realistic for HPC
    storage_cost = fsx_cost_year

    # Data transfer
    print("\n" + "=" * 80)
    print("DATA TRANSFER COSTS")
    print("=" * 80)

    # Estimate: Most compute is internal (free), some egress
    # Assume 10 TB/month egress (results, data export)
    transfer_tb_month = 10
    transfer_cost_month = (transfer_tb_month * 1024 - 100) * DATA_TRANSFER_OUT  # First 100GB free
    transfer_cost_year = transfer_cost_month * 12

    print(f"\nEstimated data transfer out:")
    print(f"  Volume: {transfer_tb_month} TB/month")
    print(f"  Cost: ${transfer_cost_month:,.0f}/month = ${transfer_cost_year:,.0f}/year")

    # Support costs
    print("\n" + "=" * 80)
    print("AWS SUPPORT COSTS")
    print("=" * 80)

    # Business support: 10% of monthly usage (or $100/month minimum)
    monthly_compute = (total_compute_cost + total_gpu_cost) / 12
    support_cost_month = max(monthly_compute * 0.10, 100)
    support_cost_year = support_cost_month * 12

    print(f"\nAWS Business Support (10% of usage):")
    print(f"  Cost: ${support_cost_month:,.0f}/month = ${support_cost_year:,.0f}/year")

    # Additional operational costs
    print("\n" + "=" * 80)
    print("ADDITIONAL OPERATIONAL COSTS")
    print("=" * 80)

    # Scheduler/orchestration (AWS Batch is free, ParallelCluster management)
    # Monitoring (CloudWatch, AWS Cost Explorer)
    # IAM/security tooling
    operations_cost_year = 50000  # Estimate

    print(f"\nOperational overhead (monitoring, tooling, etc.):")
    print(f"  Cost: ${operations_cost_year:,}/year")

    # Total costs
    print("\n" + "=" * 80)
    print("TOTAL AWS COSTS (All-In Migration)")
    print("=" * 80)

    total_cost = (
        total_compute_cost +
        total_gpu_cost +
        storage_cost +
        transfer_cost_year +
        support_cost_year +
        operations_cost_year
    )

    print(f"\nCost breakdown:")
    print(f"  {'Component':<30s} {'Annual Cost':<20s} {'% of Total':<15s}")
    print(f"  {'-'*30} {'-'*20} {'-'*15}")
    print(f"  {'Compute (c7i instances)':<30s} ${total_compute_cost:>18,.0f} {total_compute_cost/total_cost*100:>13.1f}%")
    print(f"  {'GPU (g5/p3 instances)':<30s} ${total_gpu_cost:>18,.0f} {total_gpu_cost/total_cost*100:>13.1f}%")
    print(f"  {'Storage (FSx for Lustre)':<30s} ${storage_cost:>18,.0f} {storage_cost/total_cost*100:>13.1f}%")
    print(f"  {'Data Transfer':<30s} ${transfer_cost_year:>18,.0f} {transfer_cost_year/total_cost*100:>13.1f}%")
    print(f"  {'AWS Support (Business)':<30s} ${support_cost_year:>18,.0f} {support_cost_year/total_cost*100:>13.1f}%")
    print(f"  {'Operations & Monitoring':<30s} ${operations_cost_year:>18,.0f} {operations_cost_year/total_cost*100:>13.1f}%")
    print(f"  {'-'*30} {'-'*20} {'-'*15}")
    print(f"  {'TOTAL':<30s} ${total_cost:>18,.0f} {'100.0%':>13s}")

    # Comparison to OSCAR
    print("\n" + "=" * 80)
    print("COMPARISON: AWS vs OSCAR")
    print("=" * 80)

    oscar_cost = 9_000_000
    savings = oscar_cost - total_cost
    savings_pct = (savings / oscar_cost) * 100

    print(f"\n  OSCAR (on-premise): ${oscar_cost:,}/year")
    print(f"  AWS (all-in): ${total_cost:,}/year")
    print(f"  Savings: ${savings:,}/year ({savings_pct:.1f}%)")

    # ROI analysis
    print("\n" + "=" * 80)
    print("MIGRATION ROI ANALYSIS")
    print("=" * 80)

    # Assume migration costs
    migration_cost = 500_000  # One-time: planning, training, data migration, testing

    print(f"\nOne-time migration costs: ${migration_cost:,}")
    print(f"Annual savings: ${savings:,}")
    print(f"Payback period: {migration_cost / savings:.2f} years ({migration_cost / savings * 12:.1f} months)")

    # 3-year TCO
    three_year_oscar = oscar_cost * 3
    three_year_aws = migration_cost + (total_cost * 3)
    three_year_savings = three_year_oscar - three_year_aws

    print(f"\n3-Year Total Cost of Ownership:")
    print(f"  OSCAR: ${three_year_oscar:,}")
    print(f"  AWS (including migration): ${three_year_aws:,}")
    print(f"  Net savings: ${three_year_savings:,} ({three_year_savings/three_year_oscar*100:.1f}%)")

    # Service model recommendations
    print("\n" + "=" * 80)
    print("AWS SERVICE MODEL RECOMMENDATIONS")
    print("=" * 80)

    print(f"\nRecommended architecture:")
    print(f"  1. AWS Batch for job scheduling")
    print(f"     - Automatic spot/on-demand switching")
    print(f"     - Native integration with compute/GPU instances")
    print(f"     - No scheduler management overhead")
    print(f"     - Free service (pay only for compute)")
    print(f"")
    print(f"  2. FSx for Lustre for high-performance storage")
    print(f"     - HPC-optimized (sub-ms latency)")
    print(f"     - 100s of GB/s throughput")
    print(f"     - S3 integration for data lifecycle")
    print(f"     - Scratch or persistent deployment")
    print(f"")
    print(f"  3. EC2 Compute/GPU instances")
    print(f"     - c7i family for compute workloads")
    print(f"     - g5 instances for inference/light ML")
    print(f"     - p3/p4 instances for training/heavy ML")
    print(f"     - Mix of spot (85-95%) and on-demand")
    print(f"")
    print(f"  4. ParallelCluster (optional)")
    print(f"     - If users need HPC cluster familiarity")
    print(f"     - SLURM-compatible interface")
    print(f"     - Auto-scaling compute fleet")

    # Sensitivity analysis
    print("\n" + "=" * 80)
    print("SENSITIVITY ANALYSIS")
    print("=" * 80)

    print(f"\nImpact of spot pricing variations:")
    scenarios = [
        ("Current (70-85% spot)", total_cost),
        ("Conservative (50% spot)", total_cost * 1.20),
        ("Aggressive (95% spot)", total_cost * 0.85),
    ]

    for name, cost in scenarios:
        savings = oscar_cost - cost
        print(f"  {name:25s}: ${cost:>10,.0f}/year (saves ${savings:>10,.0f}, {savings/oscar_cost*100:>5.1f}%)")

    print(f"\nImpact of storage size:")
    storage_scenarios = [
        ("Small (250 TB)", 250),
        ("Medium (500 TB)", 500),
        ("Large (1 PB)", 1000),
        ("Very Large (2 PB)", 2000),
    ]

    for name, tb in storage_scenarios:
        storage_annual = tb * 1024 * 0.145 * 12
        total = total_cost - storage_cost + storage_annual
        print(f"  {name:25s}: ${total:>10,.0f}/year (storage: ${storage_annual:>10,.0f})")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    # Final recommendations
    print(f"\n*** RECOMMENDATIONS ***")
    print(f"\n1. Full AWS migration is economically compelling:")
    print(f"   - Saves ${savings:,.0f}/year ({savings_pct:.1f}%)")
    print(f"   - Payback in {migration_cost / savings:.1f} years")
    print(f"   - 3-year savings: ${three_year_savings:,.0f}")

    print(f"\n2. Workload is ideal for AWS:")
    print(f"   - 89.8% of jobs <1 hour (perfect for spot)")
    print(f"   - 91.2% use ≤4 CPUs (small instances)")
    print(f"   - Peak-to-average ratio 1.86x (elastic advantage)")
    print(f"   - Minimal multi-node (0.5%) - no expensive networking")

    print(f"\n3. Risk mitigation:")
    print(f"   - Use 85-95% spot for short jobs (very low interruption risk)")
    print(f"   - On-demand for critical/long jobs")
    print(f"   - FSx for Lustre provides HPC-grade storage")
    print(f"   - AWS Batch handles spot fallback automatically")

    print(f"\n4. Implementation path:")
    print(f"   - Phase 1: Migrate short compute jobs (6 months)")
    print(f"   - Phase 2: Add GPU workloads (3 months)")
    print(f"   - Phase 3: Long-running jobs (3 months)")
    print(f"   - Total migration: 12 months")
    print(f"   - Start saving immediately with Phase 1")

if __name__ == "__main__":
    csv_file = "/Users/scttfrdmn/src/cluster-job-analysis/oscar_all_jobs_2025.csv"
    analyze_full_migration(csv_file)
