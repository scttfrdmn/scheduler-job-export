#!/usr/bin/env python3
"""
Analyze Cluster Configuration
Calculates actual cluster size and composition from config export
"""

import pandas as pd
import sys
import glob

if len(sys.argv) < 2:
    print("Usage: python3 analyze_cluster_config.py <config_csv_file>")
    print("")
    print("Examples:")
    print("  python3 analyze_cluster_config.py slurm_config.csv")
    print("  python3 analyze_cluster_config.py cluster_configs_*/slurm_config.csv")
    sys.exit(1)

config_file = sys.argv[1]

print("="*80)
print("CLUSTER CONFIGURATION ANALYSIS")
print("="*80)
print(f"\nFile: {config_file}")
print()

# Detect scheduler type from filename
scheduler = "unknown"
if 'slurm' in config_file.lower():
    scheduler = "SLURM"
elif 'uge' in config_file.lower() or 'sge' in config_file.lower():
    scheduler = "UGE/SGE"
elif 'pbs' in config_file.lower():
    scheduler = "PBS"
elif 'lsf' in config_file.lower():
    scheduler = "LSF"
elif 'condor' in config_file.lower():
    scheduler = "HTCondor"

print(f"Detected scheduler: {scheduler}")
print()

# Read configuration
df = pd.read_csv(config_file)

print("="*80)
print("CLUSTER SIZE & COMPOSITION")
print("="*80)
print()

if scheduler == "SLURM":
    # SLURM format: NodeName,CPUs,Memory,Gres,Partition,State,CPUAllocation
    total_nodes = len(df)
    total_cpus = df['CPUs'].sum()

    print(f"Total Nodes: {total_nodes:,}")
    print(f"Total CPUs: {total_cpus:,}")
    print()

    # CPUs per node distribution
    print("CPUs per Node Distribution:")
    cpu_dist = df.groupby('CPUs').size().sort_index()
    for cpus, count in cpu_dist.items():
        pct = count / total_nodes * 100
        total_for_type = cpus * count
        print(f"  {cpus:3d} CPUs: {count:4d} nodes ({pct:5.1f}%) = {total_for_type:,} total CPUs")
    print()

    # Memory distribution
    print("Memory per Node Distribution:")
    mem_dist = df.groupby('Memory').size().sort_index()
    for mem, count in mem_dist.items():
        pct = count / total_nodes * 100
        print(f"  {mem:6,} MB: {count:4d} nodes ({pct:5.1f}%)")
    print()

    # GPU nodes
    gpu_nodes = df[df['Gres'].str.contains('gpu', case=False, na=False)]
    print(f"GPU Nodes: {len(gpu_nodes):,} ({len(gpu_nodes)/total_nodes*100:.1f}%)")
    if len(gpu_nodes) > 0:
        print("\nGPU Types:")
        for gres_type in gpu_nodes['Gres'].value_counts().head(10).items():
            print(f"  {gres_type[0]}: {gres_type[1]} nodes")
    print()

    # Partitions
    print("Partitions:")
    for partition in df.groupby('Partition'):
        part_name = partition[0]
        part_df = partition[1]
        part_nodes = len(part_df)
        part_cpus = part_df['CPUs'].sum()
        print(f"  {part_name:20s}: {part_nodes:4d} nodes, {part_cpus:6,} CPUs")
    print()

    # Node states
    print("Node States:")
    for state in df['State'].value_counts().items():
        state_name = state[0].split('+')[0].split('*')[0]  # Remove flags
        count = state[1]
        pct = count / total_nodes * 100
        print(f"  {state_name:15s}: {count:4d} nodes ({pct:5.1f}%)")

elif scheduler == "UGE/SGE":
    # UGE format: hostname,num_proc,mem_total,slots
    total_hosts = len(df)
    total_slots = df['slots'].astype(int).sum() if 'slots' in df.columns else 0

    print(f"Total Hosts: {total_hosts:,}")
    print(f"Total Slots: {total_slots:,}")
    print()

    # Slots per host
    if 'slots' in df.columns:
        print("Slots per Host Distribution:")
        slot_dist = df.groupby('slots').size().sort_index()
        for slots, count in slot_dist.items():
            pct = count / total_hosts * 100
            total_for_type = int(slots) * count
            print(f"  {slots:3} slots: {count:4d} hosts ({pct:5.1f}%) = {total_for_type:,} total slots")

elif scheduler == "PBS":
    # PBS format: hostname,cpus,memory,state
    total_nodes = len(df)
    if 'cpus' in df.columns:
        total_cpus = df['cpus'].astype(int, errors='ignore').sum()
        print(f"Total Nodes: {total_nodes:,}")
        print(f"Total CPUs: {total_cpus:,}")
        print()

        # CPU distribution
        print("CPUs per Node Distribution:")
        cpu_dist = df.groupby('cpus').size().sort_index()
        for cpus, count in cpu_dist.items():
            pct = count / total_nodes * 100
            print(f"  {cpus} CPUs: {count:4d} nodes ({pct:5.1f}%)")

    # States
    if 'state' in df.columns:
        print("\nNode States:")
        for state in df['state'].value_counts().items():
            print(f"  {state[0]:15s}: {state[1]:4d} nodes")

elif scheduler == "LSF":
    # LSF format: hostname,status,cpus,max_jobs
    total_hosts = len(df)
    if 'cpus' in df.columns:
        total_cpus = df['cpus'].astype(int, errors='ignore').sum()
        print(f"Total Hosts: {total_hosts:,}")
        print(f"Total CPUs: {total_cpus:,}")

    # Status
    if 'status' in df.columns:
        print("\nHost Status:")
        for status in df['status'].value_counts().items():
            print(f"  {status[0]:15s}: {status[1]:4d} hosts")

elif scheduler == "HTCondor":
    # HTCondor format: Machine,Cpus,Memory,TotalSlots,State,Activity
    # Note: HTCondor may show multiple slots per machine
    total_slots = len(df)
    total_machines = df['Machine'].nunique() if 'Machine' in df.columns else 0

    print(f"Total Machines: {total_machines:,}")
    print(f"Total Slots: {total_slots:,}")

    if 'Cpus' in df.columns:
        total_cpus = df.groupby('Machine')['Cpus'].first().sum()
        print(f"Total CPUs: {total_cpus:,}")

    # States
    if 'State' in df.columns:
        print("\nSlot States:")
        for state in df['State'].value_counts().items():
            print(f"  {state[0]:15s}: {state[1]:4d} slots")

print()
print("="*80)
print("UTILIZATION CALCULATION")
print("="*80)
print()
print("To calculate actual utilization, compare this config with job data:")
print()
print("1. Actual cluster capacity (from this config)")
print("2. Peak concurrent usage (from job data)")
print("3. Mean concurrent usage (from job data)")
print()
print("Example:")
if scheduler == "SLURM":
    print(f"  Cluster capacity: {total_cpus:,} CPUs")
    print(f"  Peak usage: [from analyze_concurrent_load.py]")
    print(f"  Mean usage: [from analyze_concurrent_load.py]")
    print(f"  ")
    print(f"  Peak utilization = peak_usage / {total_cpus:,}")
    print(f"  Mean utilization = mean_usage / {total_cpus:,}")

print()
print("="*80)
