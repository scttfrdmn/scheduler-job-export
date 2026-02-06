#!/usr/bin/env python3
"""
Standardize Cluster Configuration Formats

Converts scheduler-specific config CSVs to a common standard format:
  hostname,cpus,memory_mb,node_type,state,partition,extra

This allows cross-scheduler comparison and unified analysis.
"""

import pandas as pd
import sys
import re

if len(sys.argv) < 2:
    print("Usage: python3 standardize_cluster_config.py <config_csv>")
    print("")
    print("Converts scheduler-specific config to standard format:")
    print("  hostname,cpus,memory_mb,node_type,state,partition,extra")
    print("")
    print("Supports: SLURM, UGE/SGE, PBS, LSF, HTCondor")
    sys.exit(1)

input_file = sys.argv[1]
output_file = input_file.replace('.csv', '_standardized.csv')

if len(sys.argv) > 2:
    output_file = sys.argv[2]

# Detect scheduler from filename
scheduler = None
if 'slurm' in input_file.lower():
    scheduler = 'SLURM'
elif 'uge' in input_file.lower() or 'sge' in input_file.lower():
    scheduler = 'UGE'
elif 'pbs' in input_file.lower():
    scheduler = 'PBS'
elif 'lsf' in input_file.lower():
    scheduler = 'LSF'
elif 'condor' in input_file.lower() or 'htcondor' in input_file.lower():
    scheduler = 'HTCondor'

if not scheduler:
    print("ERROR: Cannot detect scheduler from filename")
    print("Filename should contain: slurm, uge, sge, pbs, lsf, or condor")
    sys.exit(1)

print(f"Detected scheduler: {scheduler}")
print(f"Input: {input_file}")
print(f"Output: {output_file}")
print()

# Read input
df = pd.read_csv(input_file)

# Standardize based on scheduler
standardized = []

if scheduler == 'SLURM':
    # SLURM format: NodeName,CPUs,Memory,Gres,Partition,State,CPUAllocation
    for _, row in df.iterrows():
        # Determine node type from Gres
        node_type = 'compute'
        if pd.notna(row.get('Gres', '')) and 'gpu' in str(row['Gres']).lower():
            node_type = 'gpu'

        # Clean state (remove flags like +, *)
        state = str(row.get('State', '')).split('+')[0].split('*')[0]

        standardized.append({
            'hostname': row.get('NodeName', ''),
            'cpus': row.get('CPUs', 0),
            'memory_mb': row.get('Memory', 0),
            'node_type': node_type,
            'state': state.lower(),
            'partition': row.get('Partition', ''),
            'extra': row.get('Gres', '')
        })

elif scheduler == 'UGE':
    # UGE format: hostname,num_proc,mem_total,slots
    for _, row in df.iterrows():
        # UGE memory might be in different units, convert to MB
        mem = row.get('mem_total', '0')
        if isinstance(mem, str):
            # Parse formats like "128.0G" or "128000M"
            mem = mem.replace('G', '000').replace('M', '').replace('K', '')
            mem = float(mem) if mem else 0

        standardized.append({
            'hostname': row.get('hostname', ''),
            'cpus': row.get('slots', row.get('num_proc', 0)),
            'memory_mb': mem,
            'node_type': 'compute',  # UGE doesn't distinguish in qhost
            'state': 'available',  # UGE qhost only shows available hosts
            'partition': '',
            'extra': ''
        })

elif scheduler == 'PBS':
    # PBS format: hostname,cpus,memory,state
    for _, row in df.iterrows():
        # PBS memory format varies
        mem = row.get('memory', '0')
        if isinstance(mem, str):
            # Parse formats like "128gb" or "131072mb"
            mem_str = mem.lower()
            if 'gb' in mem_str:
                mem = float(mem_str.replace('gb', '')) * 1024
            elif 'mb' in mem_str:
                mem = float(mem_str.replace('mb', ''))
            elif 'kb' in mem_str:
                mem = float(mem_str.replace('kb', '')) / 1024
            else:
                mem = 0

        # PBS state values: free, offline, down, job-exclusive, etc.
        state = str(row.get('state', '')).lower()
        if 'free' in state:
            state = 'idle'
        elif 'job' in state:
            state = 'allocated'
        elif 'offline' in state or 'down' in state:
            state = 'down'

        standardized.append({
            'hostname': row.get('hostname', ''),
            'cpus': row.get('cpus', 0),
            'memory_mb': mem,
            'node_type': 'compute',  # PBS doesn't distinguish in pbsnodes
            'state': state,
            'partition': '',
            'extra': ''
        })

elif scheduler == 'LSF':
    # LSF format: hostname,status,cpus,max_jobs
    for _, row in df.iterrows():
        # LSF status: ok, closed, unavail, etc.
        status = str(row.get('status', '')).lower()
        if 'ok' in status:
            state = 'available'
        elif 'closed' in status:
            state = 'closed'
        elif 'unavail' in status:
            state = 'down'
        else:
            state = status

        standardized.append({
            'hostname': row.get('hostname', ''),
            'cpus': row.get('cpus', 0),
            'memory_mb': 0,  # LSF bhosts doesn't show memory
            'node_type': 'compute',
            'state': state,
            'partition': '',
            'extra': f"max_jobs={row.get('max_jobs', '')}"
        })

elif scheduler == 'HTCondor':
    # HTCondor format: Machine,Cpus,Memory,TotalSlots,State,Activity
    # Note: HTCondor may have multiple slots per machine
    # We'll aggregate by machine

    machines = {}
    for _, row in df.iterrows():
        machine = row.get('Machine', '')
        if machine not in machines:
            machines[machine] = {
                'hostname': machine,
                'cpus': row.get('Cpus', 0),
                'memory_mb': row.get('Memory', 0),
                'node_type': 'compute',
                'state': str(row.get('State', '')).lower(),
                'partition': '',
                'extra': f"slots={row.get('TotalSlots', 1)}"
            }

    standardized = list(machines.values())

# Convert to DataFrame
std_df = pd.DataFrame(standardized)

# Ensure consistent column order
std_df = std_df[['hostname', 'cpus', 'memory_mb', 'node_type', 'state', 'partition', 'extra']]

# Write output
std_df.to_csv(output_file, index=False)

print(f"✓ Standardized {len(std_df)} nodes")
print(f"✓ Output written to: {output_file}")
print()
print("Standard format columns:")
print("  hostname    - Node/host name")
print("  cpus        - Total CPUs/cores")
print("  memory_mb   - Total memory in MB")
print("  node_type   - compute, gpu, highmem, etc.")
print("  state       - idle, allocated, down, etc.")
print("  partition   - Queue/partition name (if applicable)")
print("  extra       - Scheduler-specific details")
print()

# Print summary
print("="*80)
print("STANDARDIZED CLUSTER SUMMARY")
print("="*80)
print()
print(f"Total Nodes: {len(std_df):,}")
print(f"Total CPUs: {std_df['cpus'].sum():,}")
print(f"Total Memory: {std_df['memory_mb'].sum()/1024/1024:.1f} TB")
print()

# Node types
print("Node Types:")
for node_type, count in std_df['node_type'].value_counts().items():
    print(f"  {node_type:10s}: {count:4d} nodes")
print()

# States
print("Node States:")
for state, count in std_df['state'].value_counts().items():
    print(f"  {state:10s}: {count:4d} nodes")
print()

# CPU distribution
print("CPU Distribution:")
cpu_dist = std_df.groupby('cpus').size().sort_index()
for cpus, count in cpu_dist.items():
    total = cpus * count
    print(f"  {cpus:3d} CPUs: {count:4d} nodes = {total:,} total CPUs")
print()
print("="*80)
