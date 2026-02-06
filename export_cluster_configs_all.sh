#!/bin/bash
#
# Export Cluster Configuration for All Schedulers
# Auto-detects which scheduler is installed and exports config
#

set -euo pipefail

OUTPUT_DIR="cluster_configs_$(date +%Y%m%d)"
mkdir -p "$OUTPUT_DIR"

echo "================================"
echo "CLUSTER CONFIGURATION EXPORT"
echo "================================"
echo ""
echo "Detecting installed schedulers..."
echo ""

FOUND_SCHEDULER=false

# ==============================================================================
# SLURM
# ==============================================================================
if command -v sinfo &> /dev/null; then
    echo "✓ Found SLURM"
    FOUND_SCHEDULER=true

    sinfo -N -o "%N,%c,%m,%G,%P,%T,%C" --noheader > "$OUTPUT_DIR/slurm_nodes.tmp"
    echo "NodeName,CPUs,Memory,Gres,Partition,State,CPUAllocation" > "$OUTPUT_DIR/slurm_config.csv"
    cat "$OUTPUT_DIR/slurm_nodes.tmp" >> "$OUTPUT_DIR/slurm_config.csv"
    rm "$OUTPUT_DIR/slurm_nodes.tmp"

    echo "  Exported: $OUTPUT_DIR/slurm_config.csv"
fi

# ==============================================================================
# UGE/SGE
# ==============================================================================
if command -v qhost &> /dev/null; then
    echo "✓ Found UGE/SGE"
    FOUND_SCHEDULER=true

    # qhost shows all execution hosts
    qhost -F -xml > "$OUTPUT_DIR/uge_hosts.xml"

    # Parse XML to CSV
    python3 << 'PYTHON_EOF'
import xml.etree.ElementTree as ET
import csv
import sys

tree = ET.parse(sys.argv[1])
root = tree.getroot()

hosts = []
for host in root.findall('.//host'):
    hostname = host.get('name')
    if hostname == 'global':
        continue

    host_data = {'hostname': hostname}

    # Extract resource values
    for hostvalue in host.findall('.//hostvalue'):
        name = hostvalue.get('name')
        value = hostvalue.text
        if name in ['num_proc', 'mem_total', 'slots']:
            host_data[name] = value

    hosts.append(host_data)

# Write CSV
with open(sys.argv[2], 'w', newline='') as f:
    fieldnames = ['hostname', 'num_proc', 'mem_total', 'slots']
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(hosts)

print(f"Exported {len(hosts)} hosts", file=sys.stderr)
PYTHON_EOF

    python3 - "$OUTPUT_DIR/uge_hosts.xml" "$OUTPUT_DIR/uge_config.csv"
    echo "  Exported: $OUTPUT_DIR/uge_config.csv"
fi

# ==============================================================================
# PBS/Torque
# ==============================================================================
if command -v pbsnodes &> /dev/null; then
    echo "✓ Found PBS/Torque"
    FOUND_SCHEDULER=true

    # pbsnodes -a shows all nodes
    pbsnodes -a > "$OUTPUT_DIR/pbs_nodes.txt"

    # Parse pbsnodes output to CSV
    python3 << 'PYTHON_EOF'
import csv
import re
import sys

nodes = []
current_node = {}

with open(sys.argv[1], 'r') as f:
    for line in f:
        line = line.strip()

        # New node
        if not line.startswith(' ') and line:
            if current_node:
                nodes.append(current_node)
            current_node = {'hostname': line}
            continue

        # Parse attributes
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            if key == 'state':
                current_node['state'] = value
            elif key == 'np':
                current_node['cpus'] = value
            elif key == 'resources_available.ncpus':
                current_node['cpus'] = value
            elif key == 'resources_available.mem':
                current_node['memory'] = value

    if current_node:
        nodes.append(current_node)

# Write CSV
with open(sys.argv[2], 'w', newline='') as f:
    fieldnames = ['hostname', 'cpus', 'memory', 'state']
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(nodes)

print(f"Exported {len(nodes)} nodes", file=sys.stderr)
PYTHON_EOF

    python3 - "$OUTPUT_DIR/pbs_nodes.txt" "$OUTPUT_DIR/pbs_config.csv"
    echo "  Exported: $OUTPUT_DIR/pbs_config.csv"
fi

# ==============================================================================
# LSF
# ==============================================================================
if command -v bhosts &> /dev/null; then
    echo "✓ Found LSF"
    FOUND_SCHEDULER=true

    # bhosts -l gives detailed info
    bhosts -w > "$OUTPUT_DIR/lsf_hosts.txt"

    # Also get lshosts for hardware info
    if command -v lshosts &> /dev/null; then
        lshosts -w > "$OUTPUT_DIR/lsf_lshosts.txt"
    fi

    # Parse bhosts output
    python3 << 'PYTHON_EOF'
import csv
import sys
import re

hosts = []

with open(sys.argv[1], 'r') as f:
    # Skip header line
    header = f.readline()

    for line in f:
        parts = line.split()
        if len(parts) >= 4:
            hosts.append({
                'hostname': parts[0],
                'status': parts[1],
                'cpus': parts[3] if len(parts) > 3 else '',
                'max_jobs': parts[4] if len(parts) > 4 else '',
            })

# Write CSV
with open(sys.argv[2], 'w', newline='') as f:
    fieldnames = ['hostname', 'status', 'cpus', 'max_jobs']
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(hosts)

print(f"Exported {len(hosts)} hosts", file=sys.stderr)
PYTHON_EOF

    python3 - "$OUTPUT_DIR/lsf_hosts.txt" "$OUTPUT_DIR/lsf_config.csv"
    echo "  Exported: $OUTPUT_DIR/lsf_config.csv"
fi

# ==============================================================================
# HTCondor
# ==============================================================================
if command -v condor_status &> /dev/null; then
    echo "✓ Found HTCondor"
    FOUND_SCHEDULER=true

    # condor_status shows all slots
    condor_status -af:ht Machine Cpus Memory TotalSlots State Activity > "$OUTPUT_DIR/condor_status.tmp"

    echo "Machine,Cpus,Memory,TotalSlots,State,Activity" > "$OUTPUT_DIR/htcondor_config.csv"
    cat "$OUTPUT_DIR/condor_status.tmp" >> "$OUTPUT_DIR/htcondor_config.csv"
    rm "$OUTPUT_DIR/condor_status.tmp"

    echo "  Exported: $OUTPUT_DIR/htcondor_config.csv"
fi

# ==============================================================================
# SUMMARY
# ==============================================================================
echo ""
if [ "$FOUND_SCHEDULER" = false ]; then
    echo "ERROR: No supported scheduler found!"
    echo ""
    echo "Supported schedulers:"
    echo "  - SLURM (sinfo)"
    echo "  - UGE/SGE (qhost)"
    echo "  - PBS/Torque (pbsnodes)"
    echo "  - LSF (bhosts)"
    echo "  - HTCondor (condor_status)"
    exit 1
fi

echo "================================"
echo "CONFIGURATION EXPORT COMPLETE"
echo "================================"
echo ""
echo "Configuration files saved in: $OUTPUT_DIR/"
echo ""
echo "Next steps:"
echo "  1. Review configuration files:"
echo "     ls -lh $OUTPUT_DIR/"
echo ""
echo "  2. Calculate cluster statistics:"
echo "     ./analyze_cluster_config.sh $OUTPUT_DIR/*.csv"
echo ""
echo "  3. Compare with job utilization data to determine true utilization"
echo ""
