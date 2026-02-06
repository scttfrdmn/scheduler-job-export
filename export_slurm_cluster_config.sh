#!/bin/bash
#
# Export SLURM Cluster Configuration/Inventory
# Shows actual cluster size and composition
#

set -euo pipefail

OUTPUT_FILE="slurm_cluster_config_$(date +%Y%m%d).csv"

echo "Exporting SLURM cluster configuration..."
echo "Output file: $OUTPUT_FILE"
echo ""

# Check if sinfo is available
if ! command -v sinfo &> /dev/null; then
    echo "ERROR: sinfo command not found. Is SLURM installed?"
    exit 1
fi

echo "Querying cluster configuration..."

# Export with sinfo - shows ALL nodes regardless of whether they ran jobs
sinfo -N -o "%N,%c,%m,%G,%P,%T,%C" --noheader > "$OUTPUT_FILE.tmp"

# Add header
echo "NodeName,CPUs,Memory,Gres,Partition,State,CPUAllocation" > "$OUTPUT_FILE"
cat "$OUTPUT_FILE.tmp" >> "$OUTPUT_FILE"
rm "$OUTPUT_FILE.tmp"

echo ""
echo "Cluster configuration exported!"
echo ""

# Calculate summary statistics
python3 << 'PYTHON_EOF'
import csv
import sys

nodes = {}
with open(sys.argv[1], 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        node = row['NodeName']
        nodes[node] = {
            'cpus': int(row['CPUs']) if row['CPUs'].isdigit() else 0,
            'memory': int(row['Memory']) if row['Memory'].isdigit() else 0,
            'gres': row['Gres'],
            'partition': row['Partition'],
            'state': row['State']
        }

print("="*80)
print("SLURM CLUSTER CONFIGURATION SUMMARY")
print("="*80)
print()
print(f"Total Nodes: {len(nodes)}")
print()

# Count by state
states = {}
for node, info in nodes.items():
    state = info['state'].split('+')[0].split('*')[0]  # Remove flags
    states[state] = states.get(state, 0) + 1

print("Nodes by State:")
for state, count in sorted(states.items()):
    print(f"  {state:15s}: {count:4d} nodes")
print()

# Count CPUs
total_cpus = sum(n['cpus'] for n in nodes.values())
cpu_counts = {}
for node, info in nodes.items():
    cpus = info['cpus']
    cpu_counts[cpus] = cpu_counts.get(cpus, 0) + 1

print(f"Total CPUs: {total_cpus:,}")
print()
print("CPUs per Node Distribution:")
for cpus, count in sorted(cpu_counts.items()):
    print(f"  {cpus:3d} CPUs: {count:4d} nodes ({count*cpus:,} total CPUs)")
print()

# GPU nodes
gpu_nodes = [n for n, info in nodes.items() if info['gres'] and 'gpu' in info['gres'].lower()]
print(f"GPU Nodes: {len(gpu_nodes)}")
if gpu_nodes:
    print("  GPU Types:")
    gpu_types = {}
    for node in gpu_nodes:
        gres = nodes[node]['gres']
        gpu_types[gres] = gpu_types.get(gres, 0) + 1
    for gtype, count in sorted(gpu_types.items()):
        print(f"    {gtype}: {count} nodes")
print()

# Partitions
partitions = {}
for node, info in nodes.items():
    part = info['partition']
    if part not in partitions:
        partitions[part] = {'nodes': 0, 'cpus': 0}
    partitions[part]['nodes'] += 1
    partitions[part]['cpus'] += info['cpus']

print("Partitions:")
for part, stats in sorted(partitions.items()):
    print(f"  {part:20s}: {stats['nodes']:4d} nodes, {stats['cpus']:6,} CPUs")

print()
print("="*80)
PYTHON_EOF

python3 - "$OUTPUT_FILE"

echo ""
echo "Configuration details saved to: $OUTPUT_FILE"
echo ""
echo "Next steps:"
echo "  1. Compare with job data to calculate true utilization"
echo "  2. Use to validate cluster size assumptions in analysis"
echo ""
