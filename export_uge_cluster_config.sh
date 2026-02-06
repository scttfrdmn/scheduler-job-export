#!/bin/bash
#
# Export UGE/SGE/OGE Cluster Configuration/Inventory
# Shows actual cluster size and composition
# Equivalent to export_slurm_cluster_config.sh
#

set -euo pipefail

OUTPUT_FILE="uge_cluster_config_$(date +%Y%m%d).csv"

echo "================================================================"
echo "UGE/SGE Cluster Configuration Export"
echo "================================================================"
echo ""
echo "Output file: $OUTPUT_FILE"
echo ""

# Check if qhost is available
if ! command -v qhost &> /dev/null; then
    echo "ERROR: qhost command not found. Is UGE/SGE installed?"
    echo ""
    echo "Grid Engine must be installed and SGE_ROOT must be set."
    echo "Try: source /path/to/sge/default/common/settings.sh"
    exit 1
fi

# Detect GE variant
GE_VARIANT="unknown"
if command -v qconf &> /dev/null; then
    VERSION_OUTPUT=$(qconf -help 2>&1 || qconf -sobjl 2>&1 || echo "")
    if echo "$VERSION_OUTPUT" | grep -qi "univa"; then
        GE_VARIANT="Univa Grid Engine (UGE)"
    elif echo "$VERSION_OUTPUT" | grep -qi "open grid"; then
        GE_VARIANT="Open Grid Engine (OGE)"
    elif echo "$VERSION_OUTPUT" | grep -qi "sun grid"; then
        GE_VARIANT="Sun Grid Engine (SGE)"
    else
        GE_VARIANT="Grid Engine"
    fi
fi

echo "Detected variant: $GE_VARIANT"
echo ""

TEMP_XML=$(mktemp)
TEMP_TEXT=$(mktemp)
trap 'rm -f "$TEMP_XML" "$TEMP_TEXT"' EXIT

echo "Querying all execution hosts with qhost..."

# Try XML output first (more reliable parsing)
if qhost -F -xml > "$TEMP_XML" 2>/dev/null; then
    echo "Using XML output format"
    USE_XML=true
else
    echo "XML not available, using text format"
    qhost -F > "$TEMP_TEXT"
    USE_XML=false
fi

echo ""
echo "Parsing qhost output into CSV format..."

# Parse qhost output into CSV
python3 << 'PYTHON_EOF'
import sys
import csv
import re
import xml.etree.ElementTree as ET

use_xml = sys.argv[1] == 'true'
xml_file = sys.argv[2]
text_file = sys.argv[3]
output_file = sys.argv[4]

hosts = []

if use_xml:
    # Parse XML output
    print("Parsing XML output...", file=sys.stderr)
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for host in root.findall('.//host'):
            hostname = host.get('name')

            # Skip global/summary entries
            if hostname in ['global', '-']:
                continue

            host_data = {
                'hostname': hostname,
                'num_proc': '',
                'num_cores': '',
                'mem_total': '',
                'mem_used': '',
                'load_avg': '',
                'arch': '',
                'slots': '',
                'slots_used': '',
                'slots_total': ''
            }

            # Extract resource values from hostvalue elements
            for hostvalue in host.findall('.//hostvalue'):
                name = hostvalue.get('name')
                value = hostvalue.text if hostvalue.text else ''

                if name == 'num_proc':
                    host_data['num_proc'] = value
                elif name == 'num_cores':
                    host_data['num_cores'] = value
                elif name == 'm_mem_total':
                    # Memory in bytes, convert to MB
                    try:
                        mem_bytes = float(value)
                        mem_mb = int(mem_bytes / (1024 * 1024))
                        host_data['mem_total'] = str(mem_mb)
                    except:
                        host_data['mem_total'] = value
                elif name == 'm_mem_used':
                    try:
                        mem_bytes = float(value)
                        mem_mb = int(mem_bytes / (1024 * 1024))
                        host_data['mem_used'] = str(mem_mb)
                    except:
                        host_data['mem_used'] = value
                elif name == 'load_avg':
                    host_data['load_avg'] = value
                elif name == 'arch':
                    host_data['arch'] = value
                elif name == 'slots':
                    host_data['slots_total'] = value
                elif name == 'slots_used':
                    host_data['slots_used'] = value

            hosts.append(host_data)

    except Exception as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        print("Falling back to text parsing...", file=sys.stderr)
        use_xml = False

if not use_xml:
    # Parse text output
    print("Parsing text output...", file=sys.stderr)
    try:
        with open(text_file, 'r') as f:
            lines = f.readlines()

        # Text format has header and data lines
        # HOSTNAME                ARCH         NCPU NSOC NCOR NTHR  LOAD  MEMTOT  MEMUSE  SWAPTO  SWAPUS
        # -------------------------------------------------------------------------------
        # global                  -               -    -    -    -     -       -       -       -       -
        # host1                   lx-amd64        32   2   16    2  1.05   128.0G    4.5G    16.0G    0.0

        in_data = False
        for line in lines:
            line = line.strip()

            # Skip separator lines
            if line.startswith('---'):
                in_data = True
                continue

            # Skip empty lines
            if not line:
                continue

            # Skip header
            if line.startswith('HOSTNAME'):
                continue

            # Skip global summary
            if line.startswith('global'):
                continue

            if in_data:
                # Parse data line
                parts = line.split()
                if len(parts) >= 2:
                    hostname = parts[0]
                    arch = parts[1] if len(parts) > 1 else ''

                    host_data = {
                        'hostname': hostname,
                        'arch': arch,
                        'num_proc': parts[2] if len(parts) > 2 and parts[2] != '-' else '',
                        'mem_total': parts[6] if len(parts) > 6 and parts[6] != '-' else '',
                        'load_avg': parts[5] if len(parts) > 5 and parts[5] != '-' else '',
                        'slots_total': parts[2] if len(parts) > 2 and parts[2] != '-' else ''  # NCPU
                    }

                    # Parse memory (format: "128.0G", "8192.0M")
                    if host_data['mem_total']:
                        mem_str = host_data['mem_total']
                        mem_match = re.match(r'([\d.]+)([GMKT])?', mem_str)
                        if mem_match:
                            mem_value = float(mem_match.group(1))
                            mem_unit = mem_match.group(2) if mem_match.group(2) else 'M'

                            # Convert to MB
                            if mem_unit == 'G':
                                mem_mb = int(mem_value * 1024)
                            elif mem_unit == 'K':
                                mem_mb = int(mem_value / 1024)
                            elif mem_unit == 'T':
                                mem_mb = int(mem_value * 1024 * 1024)
                            else:
                                mem_mb = int(mem_value)

                            host_data['mem_total'] = str(mem_mb)

                    hosts.append(host_data)

    except Exception as e:
        print(f"Error parsing text: {e}", file=sys.stderr)

print(f"Parsed {len(hosts)} hosts", file=sys.stderr)

# Write CSV
fieldnames = [
    'hostname', 'num_proc', 'mem_total_mb', 'slots_total',
    'arch', 'load_avg'
]

with open(output_file, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for host in hosts:
        # Map fields
        row = {
            'hostname': host.get('hostname', ''),
            'num_proc': host.get('num_proc', host.get('num_cores', '')),
            'mem_total_mb': host.get('mem_total', '0'),
            'slots_total': host.get('slots_total', host.get('num_proc', '')),
            'arch': host.get('arch', ''),
            'load_avg': host.get('load_avg', '')
        }
        writer.writerow(row)

print(f"Wrote {len(hosts)} hosts to {output_file}", file=sys.stderr)
PYTHON_EOF

python3 - "$USE_XML" "$TEMP_XML" "$TEMP_TEXT" "$OUTPUT_FILE"

echo ""
echo "================================================================"
echo "UGE/SGE CLUSTER CONFIGURATION SUMMARY"
echo "================================================================"

# Calculate summary statistics
python3 << 'PYTHON_EOF'
import csv
import sys

with open(sys.argv[1], 'r') as f:
    reader = csv.DictReader(f)
    hosts = list(reader)

print()
print(f"Total Execution Hosts: {len(hosts)}")
print()

# Count slots (CPUs)
total_slots = 0
slot_counts = {}
for host in hosts:
    slots_str = host['slots_total']
    if slots_str and slots_str.isdigit():
        slots = int(slots_str)
        total_slots += slots
        slot_counts[slots] = slot_counts.get(slots, 0) + 1

print(f"Total Slots (CPUs): {total_slots:,}")
print()

if slot_counts:
    print("Slots per Host Distribution:")
    for slots in sorted(slot_counts.keys()):
        count = slot_counts[slots]
        total = slots * count
        print(f"  {slots:3d} slots: {count:4d} hosts = {total:,} total slots")
    print()

# Memory summary
hosts_with_memory = [h for h in hosts if h['mem_total_mb'] and h['mem_total_mb'].isdigit() and int(h['mem_total_mb']) > 0]
if hosts_with_memory:
    total_memory_mb = sum(int(h['mem_total_mb']) for h in hosts_with_memory)
    total_memory_tb = total_memory_mb / 1024 / 1024
    print(f"Total Memory: {total_memory_tb:.1f} TB ({len(hosts_with_memory)} hosts with memory info)")
    print()

# Architecture
arch_counts = {}
for host in hosts:
    arch = host['arch'] if host['arch'] else 'unknown'
    arch_counts[arch] = arch_counts.get(arch, 0) + 1

if arch_counts:
    print("Architectures:")
    for arch in sorted(arch_counts.keys()):
        count = arch_counts[arch]
        print(f"  {arch:20s}: {count:4d} hosts")
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
echo "   ./export_uge_comprehensive.sh 01/01/2024 12/31/2024"
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
