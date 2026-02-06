#!/bin/bash
#
# Export PBS/Torque/PBS Pro Cluster Configuration/Inventory
# Shows actual cluster size and composition
# Equivalent to export_slurm_cluster_config.sh
#

set -euo pipefail

OUTPUT_FILE="pbs_cluster_config_$(date +%Y%m%d).csv"

echo "================================================================"
echo "PBS/Torque Cluster Configuration Export"
echo "================================================================"
echo ""
echo "Output file: $OUTPUT_FILE"
echo ""

# Check if pbsnodes is available
if ! command -v pbsnodes &> /dev/null; then
    echo "ERROR: pbsnodes command not found. Is PBS/Torque installed?"
    echo ""
    echo "PBS/Torque must be installed and in your PATH"
    exit 1
fi

# Detect PBS variant
PBS_VARIANT="unknown"
VERSION_OUTPUT=$(pbsnodes --version 2>&1 || echo "")
if echo "$VERSION_OUTPUT" | grep -qi "pbs pro"; then
    PBS_VARIANT="PBS Pro"
elif echo "$VERSION_OUTPUT" | grep -qi "torque"; then
    PBS_VARIANT="Torque"
elif echo "$VERSION_OUTPUT" | grep -qi "openpbs"; then
    PBS_VARIANT="OpenPBS"
else
    PBS_VARIANT="PBS"
fi

echo "Detected PBS variant: $PBS_VARIANT"
echo ""

TEMP_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE"' EXIT

echo "Querying all nodes with pbsnodes..."

# Get all node information
# -a = all nodes
# -S = show also unavailable nodes
pbsnodes -a > "$TEMP_FILE" 2>&1 || {
    echo "Warning: pbsnodes -a failed, trying without -a"
    pbsnodes > "$TEMP_FILE"
}

echo ""
echo "Parsing pbsnodes output into CSV format..."

# Parse pbsnodes output into CSV
python3 << 'PYTHON_EOF'
import sys
import csv
import re

with open(sys.argv[1], 'r') as f:
    lines = f.readlines()

nodes = []
current_node = {}

for line in lines:
    line = line.rstrip()

    # New node starts with non-indented name
    if line and not line.startswith(' ') and not line.startswith('\t'):
        # Save previous node
        if current_node and 'hostname' in current_node:
            nodes.append(current_node)

        # Start new node
        current_node = {'hostname': line.strip()}
        continue

    # Skip empty lines
    if not line.strip():
        continue

    # Parse attribute lines (indented, format: key = value)
    line = line.strip()
    if '=' in line:
        # Split on first '='
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()

        # Map PBS attributes to our fields
        if key == 'state':
            current_node['state'] = value

        elif key == 'np' or key == 'pcpus':
            # np = number of processors (Torque)
            # pcpus = physical CPUs (PBS Pro)
            current_node['cpus'] = value

        elif key == 'resources_available.ncpus':
            # PBS Pro format
            current_node['cpus'] = value

        elif key == 'resources_available.mem':
            # Memory in PBS Pro
            mem_str = value.lower()
            # Parse formats: "128gb", "131072mb", "128000000kb"
            mem_match = re.match(r'(\d+)(gb|mb|kb)?', mem_str)
            if mem_match:
                mem_value = int(mem_match.group(1))
                mem_unit = mem_match.group(2) if mem_match.group(2) else 'kb'

                # Convert to MB
                if mem_unit == 'gb':
                    mem_mb = mem_value * 1024
                elif mem_unit == 'kb':
                    mem_mb = mem_value // 1024
                else:  # mb
                    mem_mb = mem_value

                current_node['memory_mb'] = str(mem_mb)

        elif key == 'totmem' or key == 'physmem':
            # Torque format (in KB)
            try:
                mem_kb = int(value.replace('kb', ''))
                mem_mb = mem_kb // 1024
                current_node['memory_mb'] = str(mem_mb)
            except:
                pass

        elif key == 'gpus':
            current_node['gpus'] = value

        elif key == 'resources_available.ngpus':
            current_node['gpus'] = value

        elif key == 'gpu_status':
            # Parse GPU info if present
            if value and 'gpu' in value.lower():
                current_node['node_type'] = 'gpu'

        elif key == 'properties' or key == 'resources_available.feature':
            # Node properties/features
            current_node['properties'] = value
            # Check for GPU in properties
            if 'gpu' in value.lower():
                current_node['node_type'] = 'gpu'

# Add last node
if current_node and 'hostname' in current_node:
    nodes.append(current_node)

print(f"Parsed {len(nodes)} nodes", file=sys.stderr)

# Set defaults and node types
for node in nodes:
    # Default values
    if 'cpus' not in node:
        node['cpus'] = '1'
    if 'memory_mb' not in node:
        node['memory_mb'] = '0'
    if 'state' not in node:
        node['state'] = 'unknown'

    # Determine node type
    if 'node_type' not in node:
        if node.get('gpus') and int(node.get('gpus', '0')) > 0:
            node['node_type'] = 'gpu'
        else:
            node['node_type'] = 'compute'

    # Simplify state
    # PBS states: free, job-exclusive, job-sharing, busy, down, offline, etc.
    state = node['state'].lower()
    if 'free' in state:
        node['state_simplified'] = 'idle'
    elif 'job' in state or 'busy' in state:
        node['state_simplified'] = 'allocated'
    elif 'down' in state or 'offline' in state:
        node['state_simplified'] = 'down'
    else:
        node['state_simplified'] = state

# Write CSV
fieldnames = [
    'hostname', 'cpus', 'memory_mb', 'node_type', 'state',
    'state_simplified', 'gpus', 'properties'
]

with open(sys.argv[2], 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for node in nodes:
        # Ensure all fields exist
        row = {k: node.get(k, '') for k in fieldnames}
        writer.writerow(row)

print(f"Wrote {len(nodes)} nodes to {sys.argv[2]}", file=sys.stderr)
PYTHON_EOF

python3 - "$TEMP_FILE" "$OUTPUT_FILE"

echo ""
echo "================================================================"
echo "PBS CLUSTER CONFIGURATION SUMMARY"
echo "================================================================"

# Calculate summary statistics
python3 << 'PYTHON_EOF'
import csv
import sys

with open(sys.argv[1], 'r') as f:
    reader = csv.DictReader(f)
    nodes = list(reader)

print()
print(f"Total Nodes: {len(nodes)}")
print()

# Count by state
state_counts = {}
for node in nodes:
    state = node['state_simplified']
    state_counts[state] = state_counts.get(state, 0) + 1

print("Nodes by State:")
for state in sorted(state_counts.keys()):
    count = state_counts[state]
    pct = count / len(nodes) * 100
    print(f"  {state:15s}: {count:4d} nodes ({pct:5.1f}%)")
print()

# Count CPUs
total_cpus = 0
cpu_counts = {}
for node in nodes:
    cpus_str = node['cpus']
    if cpus_str and cpus_str.isdigit():
        cpus = int(cpus_str)
        total_cpus += cpus
        cpu_counts[cpus] = cpu_counts.get(cpus, 0) + 1

print(f"Total CPUs: {total_cpus:,}")
print()

if cpu_counts:
    print("CPUs per Node Distribution:")
    for cpus in sorted(cpu_counts.keys()):
        count = cpu_counts[cpus]
        total = cpus * count
        print(f"  {cpus:3d} CPUs: {count:4d} nodes = {total:,} total CPUs")
    print()

# Memory summary
nodes_with_memory = [n for n in nodes if n['memory_mb'] and n['memory_mb'].isdigit() and int(n['memory_mb']) > 0]
if nodes_with_memory:
    total_memory_mb = sum(int(n['memory_mb']) for n in nodes_with_memory)
    total_memory_tb = total_memory_mb / 1024 / 1024
    print(f"Total Memory: {total_memory_tb:.1f} TB ({len(nodes_with_memory)} nodes with memory info)")
    print()

# Node types
type_counts = {}
for node in nodes:
    ntype = node['node_type']
    type_counts[ntype] = type_counts.get(ntype, 0) + 1

print("Node Types:")
for ntype in sorted(type_counts.keys()):
    count = type_counts[ntype]
    pct = count / len(nodes) * 100
    print(f"  {ntype:10s}: {count:4d} nodes ({pct:5.1f}%)")

# GPU nodes
gpu_nodes = [n for n in nodes if n.get('gpus') and int(n.get('gpus', '0')) > 0]
if gpu_nodes:
    total_gpus = sum(int(n['gpus']) for n in gpu_nodes)
    print(f"\nGPU Details:")
    print(f"  GPU Nodes: {len(gpu_nodes)}")
    print(f"  Total GPUs: {total_gpus}")

print()
print("="*80)
PYTHON_EOF

python3 - "$OUTPUT_FILE"

echo ""
echo "================================================================"
echo "EXPORT COMPLETE"
echo "================================================================"
echo ""
echo "Configuration file: $OUTPUT_FILE"
echo ""
echo "Next steps:"
echo ""
echo "1. Review the configuration:"
echo "   head -20 $OUTPUT_FILE"
echo ""
echo "2. Standardize format (for cross-scheduler comparison):"
echo "   python3 standardize_cluster_config.py $OUTPUT_FILE"
echo ""
echo "3. Compare with job data to calculate utilization:"
echo "   # Export job data first:"
echo "   ./export_pbs_comprehensive.sh 20240101 20241231"
echo "   "
echo "   # Then analyze utilization:"
echo "   python3 analyze_concurrent_load.py"
echo ""
echo "4. Calculate true utilization:"
echo "   # From this config: Total capacity"
echo "   # From job data: Peak and mean usage"
echo "   # Utilization = usage / capacity"
echo ""
echo "================================================================"
echo ""
