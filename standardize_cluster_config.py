#!/usr/bin/env python3
"""
Standardize Cluster Configuration Formats

Converts scheduler-specific config CSVs to a common standard format:
  hostname,cpus,memory_mb,node_type,state,partition,extra

This allows cross-scheduler comparison and unified analysis.
"""

import csv
import sys
from collections import Counter

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
with open(input_file, newline='') as fh:
    reader = csv.DictReader(fh)
    rows = list(reader)

# Standardize based on scheduler
standardized = []

if scheduler == 'SLURM':
    # SLURM format: NodeName,CPUs,Memory,Gres,Partition,State,CPUAllocation
    for row in rows:
        gres = row.get('Gres', '') or ''
        node_type = 'gpu' if 'gpu' in gres.lower() else 'compute'

        # Remove state flags like + and *
        state = (row.get('State', '') or '').split('+')[0].split('*')[0].lower()

        standardized.append({
            'hostname': row.get('NodeName', ''),
            'cpus': int(row.get('CPUs', 0) or 0),
            'memory_mb': int(row.get('Memory', 0) or 0),
            'node_type': node_type,
            'state': state,
            'partition': row.get('Partition', ''),
            'extra': gres,
        })

elif scheduler == 'UGE':
    # UGE format: hostname,num_proc,mem_total,slots
    for row in rows:
        mem = row.get('mem_total', '0') or '0'
        if isinstance(mem, str):
            # Parse formats like "128.0G" or "128000M"
            mem = mem.replace('G', '000').replace('M', '').replace('K', '')
            mem = float(mem) if mem else 0

        standardized.append({
            'hostname': row.get('hostname', ''),
            'cpus': int(row.get('slots', row.get('num_proc', 0)) or 0),
            'memory_mb': int(float(mem)),
            'node_type': 'compute',
            'state': 'available',
            'partition': '',
            'extra': '',
        })

elif scheduler == 'PBS':
    # PBS format: hostname,cpus,memory,state
    for row in rows:
        mem_str = (row.get('memory', '0') or '0').lower()
        if 'gb' in mem_str:
            mem = float(mem_str.replace('gb', '')) * 1024
        elif 'mb' in mem_str:
            mem = float(mem_str.replace('mb', ''))
        elif 'kb' in mem_str:
            mem = float(mem_str.replace('kb', '')) / 1024
        else:
            mem = 0

        state = (row.get('state', '') or '').lower()
        if 'free' in state:
            state = 'idle'
        elif 'job' in state:
            state = 'allocated'
        elif 'offline' in state or 'down' in state:
            state = 'down'

        standardized.append({
            'hostname': row.get('hostname', ''),
            'cpus': int(row.get('cpus', 0) or 0),
            'memory_mb': int(mem),
            'node_type': 'compute',
            'state': state,
            'partition': '',
            'extra': '',
        })

elif scheduler == 'LSF':
    # LSF format: hostname,status,cpus,max_jobs
    for row in rows:
        status = (row.get('status', '') or '').lower()
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
            'cpus': int(row.get('cpus', 0) or 0),
            'memory_mb': 0,  # LSF bhosts doesn't report memory
            'node_type': 'compute',
            'state': state,
            'partition': '',
            'extra': f"max_jobs={row.get('max_jobs', '')}",
        })

elif scheduler == 'HTCondor':
    # HTCondor format: Machine,Cpus,Memory,TotalSlots,State,Activity
    # Aggregate multiple slots per machine, keeping first-seen metadata
    machines = {}
    for row in rows:
        machine = row.get('Machine', '')
        if machine not in machines:
            machines[machine] = {
                'hostname': machine,
                'cpus': int(row.get('Cpus', 0) or 0),
                'memory_mb': int(row.get('Memory', 0) or 0),
                'node_type': 'compute',
                'state': (row.get('State', '') or '').lower(),
                'partition': '',
                'extra': f"slots={row.get('TotalSlots', 1)}",
            }
    standardized = list(machines.values())

COLUMNS = ['hostname', 'cpus', 'memory_mb', 'node_type', 'state', 'partition', 'extra']

with open(output_file, 'w', newline='') as fh:
    writer = csv.DictWriter(fh, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerows(standardized)

print(f"✓ Standardized {len(standardized)} nodes")
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

# Summary stats using stdlib only
total_cpus = sum(r['cpus'] for r in standardized)
total_mem_mb = sum(r['memory_mb'] for r in standardized)
node_types = Counter(r['node_type'] for r in standardized)
states = Counter(r['state'] for r in standardized)
cpu_dist = Counter(r['cpus'] for r in standardized)

print("=" * 80)
print("STANDARDIZED CLUSTER SUMMARY")
print("=" * 80)
print()
print(f"Total Nodes: {len(standardized):,}")
print(f"Total CPUs: {total_cpus:,}")
print(f"Total Memory: {total_mem_mb / 1024 / 1024:.1f} TB")
print()

print("Node Types:")
for node_type, count in sorted(node_types.items()):
    print(f"  {node_type:10s}: {count:4d} nodes")
print()

print("Node States:")
for state, count in sorted(states.items()):
    print(f"  {state:10s}: {count:4d} nodes")
print()

print("CPU Distribution:")
for cpus, count in sorted(cpu_dist.items()):
    total = cpus * count
    print(f"  {cpus:3d} CPUs: {count:4d} nodes = {total:,} total CPUs")
print()
print("=" * 80)
