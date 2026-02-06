#!/bin/bash
#
# Export LSF Cluster Configuration/Inventory
# Shows actual cluster size and composition
# Equivalent to export_slurm_cluster_config.sh
#

set -euo pipefail

OUTPUT_FILE="lsf_cluster_config_$(date +%Y%m%d).csv"

echo "================================================================"
echo "LSF Cluster Configuration Export"
echo "================================================================"
echo ""
echo "Output file: $OUTPUT_FILE"
echo ""

# Check if LSF commands are available
if ! command -v bhosts &> /dev/null; then
    echo "ERROR: bhosts command not found. Is LSF installed?"
    echo ""
    echo "LSF must be installed and LSF_ENVDIR must be set."
    echo "Try: source /path/to/lsf/conf/profile.lsf"
    exit 1
fi

if ! command -v lshosts &> /dev/null; then
    echo "WARNING: lshosts command not found."
    echo "Will use bhosts only (less detailed hardware info)"
fi

TEMP_BHOSTS=$(mktemp)
TEMP_LSHOSTS=$(mktemp)
trap 'rm -f "$TEMP_BHOSTS" "$TEMP_LSHOSTS"' EXIT

echo "Querying LSF host information..."
echo ""

# Get bhosts output (host status and load)
echo "Running: bhosts -w"
bhosts -w > "$TEMP_BHOSTS"

# Get lshosts output (hardware details) if available
if command -v lshosts &> /dev/null; then
    echo "Running: lshosts -w"
    lshosts -w > "$TEMP_LSHOSTS"
fi

# Get detailed host info with bhosts -l for resource info
TEMP_BHOSTS_DETAIL=$(mktemp)
trap 'rm -f "$TEMP_BHOSTS" "$TEMP_LSHOSTS" "$TEMP_BHOSTS_DETAIL"' EXIT

echo "Running: bhosts -l (detailed host info)"
bhosts -l > "$TEMP_BHOSTS_DETAIL"

echo ""
echo "Parsing LSF host data into CSV format..."

# Parse LSF output into CSV
python3 << 'PYTHON_EOF'
import sys
import csv
import re

bhosts_file = sys.argv[1]
lshosts_file = sys.argv[2]
bhosts_detail_file = sys.argv[3]
output_file = sys.argv[4]

# Parse bhosts -w output
# Format:
# HOST_NAME   STATUS  JL/U  MAX  NJOBS  RUN  SSUSP  USUSP  RSV
# host1       ok      -     16   2      2    0      0      0

hosts = {}

print("Parsing bhosts output...", file=sys.stderr)
with open(bhosts_file, 'r') as f:
    lines = f.readlines()

# Skip header
for line in lines[1:]:
    parts = line.split()
    if len(parts) >= 4:
        hostname = parts[0]
        status = parts[1]
        max_slots = parts[3]

        hosts[hostname] = {
            'hostname': hostname,
            'status': status,
            'max_slots': max_slots,
            'cpus': max_slots,  # Default to max_slots, may be refined
            'memory_mb': '',
            'ncpus': '',
            'ncores': '',
            'nthreads': '',
            'model': '',
            'type': ''
        }

# Parse lshosts -w output if available
# Format:
# HOST_NAME   type  model  cpuf  ncpus  ncores  nthreads  memory  swap
# host1       linux x86_64  20.0  32     16      2        128000  128000

if lshosts_file:
    print("Parsing lshosts output...", file=sys.stderr)
    try:
        with open(lshosts_file, 'r') as f:
            lines = f.readlines()

        # Skip header
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 8:
                hostname = parts[0]
                if hostname in hosts:
                    hosts[hostname]['type'] = parts[1]
                    hosts[hostname]['model'] = parts[2]
                    hosts[hostname]['ncpus'] = parts[4]
                    hosts[hostname]['ncores'] = parts[5]
                    hosts[hostname]['nthreads'] = parts[6]

                    # Memory from lshosts (in MB)
                    try:
                        memory = int(parts[7])
                        hosts[hostname]['memory_mb'] = str(memory)
                    except:
                        pass

                    # Use ncpus as cpus (more accurate than max_slots)
                    try:
                        cpus = int(parts[4])
                        hosts[hostname]['cpus'] = str(cpus)
                    except:
                        pass
    except Exception as e:
        print(f"Warning: Could not parse lshosts: {e}", file=sys.stderr)

# Parse bhosts -l output for detailed resource info
print("Parsing bhosts -l output...", file=sys.stderr)
try:
    with open(bhosts_detail_file, 'r') as f:
        lines = f.readlines()

    current_host = None
    for line in lines:
        # New host section
        if line.startswith('HOST '):
            host_match = re.search(r'HOST\s+(\S+)', line)
            if host_match:
                current_host = host_match.group(1)
            continue

        if current_host and current_host in hosts:
            # Look for resource lines
            # Example: "  RESOURCES: mem 128000M..."
            if 'RESOURCES:' in line or 'mem' in line.lower():
                mem_match = re.search(r'mem\s+(\d+)M', line)
                if mem_match:
                    hosts[current_host]['memory_mb'] = mem_match.group(1)

except Exception as e:
    print(f"Warning: Could not parse bhosts -l: {e}", file=sys.stderr)

print(f"Parsed {len(hosts)} hosts", file=sys.stderr)

# Write CSV
fieldnames = [
    'hostname', 'status', 'cpus', 'ncores', 'nthreads',
    'memory_mb', 'max_slots', 'type', 'model'
]

with open(output_file, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(hosts.values())

print(f"Wrote {len(hosts)} hosts to {output_file}", file=sys.stderr)
PYTHON_EOF

python3 - "$TEMP_BHOSTS" "$TEMP_LSHOSTS" "$TEMP_BHOSTS_DETAIL" "$OUTPUT_FILE"

echo ""
echo "================================================================"
echo "LSF CLUSTER CONFIGURATION SUMMARY"
echo "================================================================"

# Calculate summary statistics
python3 << 'PYTHON_EOF'
import csv
import sys

with open(sys.argv[1], 'r') as f:
    reader = csv.DictReader(f)
    hosts = list(reader)

print()
print(f"Total Hosts: {len(hosts)}")
print()

# Count by status
status_counts = {}
for host in hosts:
    status = host['status']
    status_counts[status] = status_counts.get(status, 0) + 1

print("Hosts by Status:")
for status, count in sorted(status_counts.items()):
    print(f"  {status:15s}: {count:4d} hosts")
print()

# Count CPUs
total_cpus = 0
cpu_counts = {}
for host in hosts:
    cpus_str = host['cpus']
    if cpus_str and cpus_str.isdigit():
        cpus = int(cpus_str)
        total_cpus += cpus
        cpu_counts[cpus] = cpu_counts.get(cpus, 0) + 1

print(f"Total CPUs: {total_cpus:,}")
print()

if cpu_counts:
    print("CPUs per Host Distribution:")
    for cpus, count in sorted(cpu_counts.items()):
        total = cpus * count
        print(f"  {cpus:3d} CPUs: {count:4d} hosts = {total:,} total CPUs")
    print()

# Memory summary
hosts_with_memory = [h for h in hosts if h['memory_mb'] and h['memory_mb'].isdigit()]
if hosts_with_memory:
    total_memory_mb = sum(int(h['memory_mb']) for h in hosts_with_memory)
    total_memory_tb = total_memory_mb / 1024 / 1024
    print(f"Total Memory: {total_memory_tb:.1f} TB ({len(hosts_with_memory)} hosts with memory info)")
    print()

# Host types
type_counts = {}
for host in hosts:
    htype = host['type'] if host['type'] else 'unknown'
    type_counts[htype] = type_counts.get(htype, 0) + 1

if len(type_counts) > 1 or 'unknown' not in type_counts:
    print("Host Types:")
    for htype, count in sorted(type_counts.items()):
        print(f"  {htype:15s}: {count:4d} hosts")
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
echo "   ./export_lsf_comprehensive.sh"
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
