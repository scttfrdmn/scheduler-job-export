#!/bin/bash
#
# Comprehensive UGE/SGE/OGE Job Data Export with User/Group Information
# Compatible with anonymize_cluster_data.sh and all analysis tools
#
# Equivalent to export_with_users.sh for SLURM
#
# Supports: Univa Grid Engine (UGE), Sun Grid Engine (SGE), Open Grid Engine (OGE)
#
# NOTE: Parallel Environment (PE) job handling:
#  - PE name captured in 'pe_name' field (e.g., "mpi", "smp", "openmpi")
#  - Node count estimated for large PE jobs (slots >= 48 cores)
#  - qacct limitation: only shows one hostname for multi-node PE jobs
#

set -euo pipefail

# Load security libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/validation.sh"
source "$SCRIPT_DIR/security_logging.sh"

# Configuration
START_DATE="${1:-01/01/$(date -d '1 year ago' +%Y 2>/dev/null || date -v-1y +%Y)}"
END_DATE="${2:-$(date +%m/%d/%Y)}"
OUTPUT_FILE="uge_jobs_with_users_$(date +%Y%m%d).csv"

# Validate and sanitize date inputs
if ! START_DATE=$(validate_and_sanitize_date "$START_DATE" "uge"); then
    log_validation_failure "date" "$START_DATE"
    echo "ERROR: Invalid start date format" >&2
    echo "Expected: MM/DD/YYYY (e.g., 01/31/2024)" >&2
    exit 1
fi

if ! END_DATE=$(validate_and_sanitize_date "$END_DATE" "uge"); then
    log_validation_failure "date" "$END_DATE"
    echo "ERROR: Invalid end date format" >&2
    echo "Expected: MM/DD/YYYY (e.g., 12/31/2024)" >&2
    exit 1
fi

echo "================================================================"
echo "UGE/SGE Comprehensive Job Data Export"
echo "================================================================"
echo ""
echo "Date range: $START_DATE to $END_DATE"
echo "Output file: $OUTPUT_FILE"
echo ""

# Log export start
log_export_start "UGE" "start=$START_DATE end=$END_DATE output=$OUTPUT_FILE"

# Check if qacct is available
if ! command -v qacct &> /dev/null; then
    echo "ERROR: qacct command not found. Is UGE/SGE installed?"
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

# Check accounting file access
if [ -n "$SGE_ROOT" ]; then
    ACCT_FILE="$SGE_ROOT/default/common/accounting"
    if [ -f "$ACCT_FILE" ]; then
        echo "Found accounting file: $ACCT_FILE"
    fi
fi

TEMP_FILE=$(mktemp)
PE_CONFIG_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE" "$PE_CONFIG_FILE"' EXIT

# Query PE configurations for better node count estimation
if command -v qconf &> /dev/null; then
    echo "Querying parallel environment configurations..."
    # Get list of all PEs
    PE_LIST=$(qconf -spl 2>/dev/null || echo "")

    if [ -n "$PE_LIST" ]; then
        # For each PE, get its allocation rule
        echo "pe_name,allocation_rule,slots_per_host" > "$PE_CONFIG_FILE"

        for pe in $PE_LIST; do
            PE_DETAILS=$(qconf -sp "$pe" 2>/dev/null || echo "")
            if [ -n "$PE_DETAILS" ]; then
                # Extract allocation_rule
                ALLOC_RULE=$(echo "$PE_DETAILS" | grep "^allocation_rule" | awk '{print $2}')

                # Determine slots per host from allocation rule
                if [[ "$ALLOC_RULE" =~ ^[0-9]+$ ]]; then
                    # Fixed number = slots per host
                    SLOTS_PER_HOST="$ALLOC_RULE"
                elif [[ "$ALLOC_RULE" == "\$pe_slots" ]]; then
                    # All on one host (SMP)
                    SLOTS_PER_HOST="SMP"
                elif [[ "$ALLOC_RULE" == "\$fill_up" ]]; then
                    SLOTS_PER_HOST="fill_up"
                elif [[ "$ALLOC_RULE" == "\$round_robin" ]]; then
                    SLOTS_PER_HOST="round_robin"
                else
                    SLOTS_PER_HOST="unknown"
                fi

                echo "$pe,$ALLOC_RULE,$SLOTS_PER_HOST" >> "$PE_CONFIG_FILE"
            fi
        done

        NUM_PES=$(tail -n +2 "$PE_CONFIG_FILE" | wc -l | tr -d ' ')
        echo "Found $NUM_PES parallel environments"
    else
        echo "No parallel environments configured or access denied"
    fi
    echo ""
fi

echo "Querying accounting database with qacct..."
echo "This may take several minutes for large date ranges..."
echo ""

# Run qacct
# -b begin_time (MM/DD/YYYY format)
# -e end_time (MM/DD/YYYY format)
# -j for all jobs (optional job ID filter)

qacct -b "$START_DATE" -e "$END_DATE" > "$TEMP_FILE" 2>&1 || {
    echo "ERROR: qacct query failed"
    echo ""
    echo "Common issues:"
    echo "  - SGE_ROOT not set"
    echo "  - Accounting file not readable"
    echo "  - Date format incorrect (should be MM/DD/YYYY)"
    echo ""
    cat "$TEMP_FILE"
    exit 1
}

echo ""
echo "Parsing qacct output into standardized CSV format..."

# Parse qacct output into CSV
python3 << 'PYTHON_EOF'
import sys
import csv
import re
from datetime import datetime

temp_file = sys.argv[1]
pe_config_file = sys.argv[2]
output_file = sys.argv[3]

# Read PE configurations
pe_configs = {}
try:
    with open(pe_config_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            pe_configs[row['pe_name']] = {
                'allocation_rule': row['allocation_rule'],
                'slots_per_host': row['slots_per_host']
            }
    print(f"Loaded {len(pe_configs)} PE configurations", file=sys.stderr)
except:
    print("No PE configurations available", file=sys.stderr)

with open(temp_file, 'r') as f:
    lines = f.readlines()

# qacct output format:
# ==============================================================
# qname        queue_name
# hostname     hostname
# group        group_name
# owner        username
# ...
# ==============================================================

records = []
current_record = {}
in_record = False

for line in lines:
    line = line.rstrip()

    # Record separator
    if line.startswith('===='):
        if current_record and 'job_number' in current_record:
            records.append(current_record)
        current_record = {}
        in_record = True
        continue

    # Skip empty lines
    if not line.strip():
        continue

    # Skip header/summary lines
    if line.startswith('ACCOUNTING SUMMARY') or line.startswith('Total'):
        continue

    # Parse key-value pairs
    # Format: "key          value" (multiple spaces)
    if in_record and len(line) > 0 and not line.startswith(' '):
        # Split on whitespace, but key and value are separated by multiple spaces
        parts = re.split(r'\s{2,}', line, maxsplit=1)
        if len(parts) == 2:
            key = parts[0].strip()
            value = parts[1].strip()

            # Map UGE fields to standard fields
            if key == 'qname':
                current_record['queue'] = value

            elif key == 'hostname':
                current_record['nodelist'] = value
                # Don't set nodes count here - will calculate after parsing all fields

            elif key == 'group':
                current_record['group'] = value

            elif key == 'owner':
                current_record['user'] = value

            elif key == 'project':
                current_record['account'] = value

            elif key == 'department':
                if 'account' not in current_record:
                    current_record['account'] = value

            elif key == 'jobname':
                current_record['job_name'] = value

            elif key == 'jobnumber':
                current_record['job_id'] = value
                current_record['job_number'] = value

            elif key == 'taskid':
                # Array job task ID
                task_id = value
                if task_id != 'undefined' and 'job_id' in current_record:
                    current_record['job_id'] = f"{current_record['job_id']}.{task_id}"

            elif key == 'slots':
                current_record['slots'] = value
                current_record['cpus_req'] = value

            elif key == 'granted_pe':
                # Parallel environment name (e.g., "mpi", "smp", "openmpi")
                # If this is set, the job used a PE and may span multiple nodes
                if value != 'NONE' and value != 'undefined':
                    current_record['pe_name'] = value
                    current_record['is_parallel'] = True

            elif key == 'pe_taskid':
                # Parallel environment task ID
                if value != 'undefined':
                    current_record['pe_tasks'] = value

            elif key == 'maxvmem':
                # Maximum virtual memory USED (not requested!)
                mem_str = value
                # Parse formats: "8.000G", "8192.000M", "8388608.000K"
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
                    else:  # M
                        mem_mb = int(mem_value)

                    current_record['mem_used'] = str(mem_mb)

            elif key == 'cpu':
                # CPU time used (in seconds)
                try:
                    current_record['cpu_time_used'] = str(float(value))
                except:
                    pass

            elif key == 'wallclock':
                # Walltime used (in seconds)
                try:
                    current_record['walltime_used'] = str(int(float(value)))
                except:
                    pass

            elif key == 'ru_maxrss':
                # Maximum resident set size (if maxvmem not available)
                if 'mem_req' not in current_record:
                    # This is in KB typically
                    try:
                        mem_kb = float(value)
                        mem_mb = int(mem_kb / 1024)
                        current_record['mem_req'] = str(mem_mb)
                    except:
                        pass

            elif key == 'submission_time':
                # Parse UGE date format
                # Format: "Mon Jan  1 00:00:00 2024"
                try:
                    # Try different formats
                    for fmt in ['%a %b %d %H:%M:%S %Y', '%m/%d/%Y %H:%M:%S']:
                        try:
                            dt = datetime.strptime(value, fmt)
                            current_record['submit_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            break
                        except ValueError:
                            continue
                except:
                    pass

            elif key == 'start_time':
                try:
                    for fmt in ['%a %b %d %H:%M:%S %Y', '%m/%d/%Y %H:%M:%S']:
                        try:
                            dt = datetime.strptime(value, fmt)
                            current_record['start_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            break
                        except ValueError:
                            continue
                except:
                    pass

            elif key == 'end_time':
                try:
                    for fmt in ['%a %b %d %H:%M:%S %Y', '%m/%d/%Y %H:%M:%S']:
                        try:
                            dt = datetime.strptime(value, fmt)
                            current_record['end_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            break
                        except ValueError:
                            continue
                except:
                    pass

            elif key == 'failed':
                # Exit status (0 = success, non-zero = failure)
                current_record['exit_status'] = value

            elif key == 'exit_status':
                current_record['exit_status'] = value

# Add last record
if current_record and 'job_number' in current_record:
    records.append(current_record)

# Post-process records to calculate node counts for PE jobs
for rec in records:
    # Calculate nodes based on PE configuration and slots
    if 'nodes' not in rec or not rec['nodes']:
        if rec.get('is_parallel'):
            # Parallel environment job - use PE config if available
            slots = int(rec.get('slots', 1))
            pe_name = rec.get('pe_name', '')

            if pe_name in pe_configs:
                # Use PE configuration
                pe_config = pe_configs[pe_name]
                slots_per_host = pe_config['slots_per_host']

                if slots_per_host == 'SMP':
                    # All slots on one host
                    rec['nodes'] = '1'
                elif slots_per_host.isdigit():
                    # Fixed slots per host
                    nodes = max(1, (slots + int(slots_per_host) - 1) // int(slots_per_host))
                    rec['nodes'] = str(nodes)
                elif slots_per_host in ['fill_up', 'round_robin']:
                    # Can't determine node count without runtime info
                    # Use heuristic: if slots > 48, likely multi-node
                    if slots >= 48:
                        rec['nodes'] = str(max(1, (slots + 23) // 24))
                    else:
                        rec['nodes'] = '1'
                else:
                    # Unknown allocation rule
                    rec['nodes'] = '1'
            else:
                # No PE config available - use heuristic
                if slots >= 48:
                    # Estimate nodes (assuming 24 cores/node average)
                    estimated_nodes = max(1, (slots + 23) // 24)
                    rec['nodes'] = str(estimated_nodes)
                else:
                    # Could be single or multi-node, can't determine
                    rec['nodes'] = '1'
        else:
            # Non-PE job, definitely single node
            rec['nodes'] = '1'

print(f"Parsed {len(records)} job records from qacct", file=sys.stderr)

# Write CSV with standardized columns (plus UGE-specific PE fields)
fieldnames = [
    'user', 'group', 'account', 'job_id', 'job_name', 'queue',
    'cpus_req', 'mem_req', 'nodes', 'nodelist', 'submit_time',
    'start_time', 'end_time', 'exit_status', 'pe_name', 'slots',
    'mem_used', 'cpu_time_used', 'walltime_used'
]

output_records = []
for rec in records:
    # Ensure all fields exist with defaults
    row = {k: rec.get(k, '') for k in fieldnames}

    # Set reasonable defaults
    if not row['cpus_req']:
        row['cpus_req'] = row.get('slots', '1')  # Use slots if cpus_req not set
    if not row['nodes']:
        row['nodes'] = '1'
    if not row['group']:
        row['group'] = 'unknown'

    output_records.append(row)

with open(output_file, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output_records)

print(f"Wrote {len(output_records)} records to {output_file}", file=sys.stderr)

# Print statistics
print("\n" + "="*80, file=sys.stderr)
print("EXPORT STATISTICS", file=sys.stderr)
print("="*80, file=sys.stderr)

unique_users = len(set(r['user'] for r in output_records if r['user']))
unique_groups = len(set(r['group'] for r in output_records if r['group']))
unique_queues = len(set(r['queue'] for r in output_records if r['queue']))
pe_jobs = len([r for r in output_records if r.get('pe_name')])
unique_pes = len(set(r.get('pe_name', '') for r in output_records if r.get('pe_name')))

print(f"\nJobs exported: {len(output_records):,}", file=sys.stderr)
print(f"Unique users: {unique_users:,}", file=sys.stderr)
print(f"Unique groups: {unique_groups:,}", file=sys.stderr)
print(f"Unique queues: {unique_queues:,}", file=sys.stderr)
if pe_jobs > 0:
    print(f"PE jobs: {pe_jobs:,} ({pe_jobs*100//len(output_records)}%)", file=sys.stderr)
    print(f"Unique PEs: {unique_pes:,}", file=sys.stderr)

# Date range
dates_with_jobs = [r['submit_time'] for r in output_records if r['submit_time']]
if dates_with_jobs:
    min_date = min(dates_with_jobs)
    max_date = max(dates_with_jobs)
    print(f"Date range: {min_date[:10]} to {max_date[:10]}", file=sys.stderr)

print(file=sys.stderr)
PYTHON_EOF

python3 - "$TEMP_FILE" "$PE_CONFIG_FILE" "$OUTPUT_FILE"

echo ""
echo "================================================================"
echo "EXPORT COMPLETE"
echo "================================================================"
echo ""
echo "Output file: $OUTPUT_FILE"
echo ""
echo "File details:"
ls -lh "$OUTPUT_FILE"
echo ""
echo "First few records:"
head -5 "$OUTPUT_FILE"
echo ""
echo "================================================================"
echo "NEXT STEPS"
echo "================================================================"
echo ""
echo "1. Verify the export looks correct:"
echo "   head -20 $OUTPUT_FILE"
echo "   tail -20 $OUTPUT_FILE"
echo ""
echo "2. Check statistics:"
echo "   wc -l $OUTPUT_FILE"
echo "   cut -d, -f1 $OUTPUT_FILE | sort -u | wc -l  # Unique users"
echo ""
echo "3. Anonymize the data:"
echo "   ./anonymize_cluster_data.sh \\"
echo "     $OUTPUT_FILE \\"
echo "     uge_jobs_anonymized.csv \\"
echo "     uge_mapping_secure.txt"
echo ""
echo "4. Secure the mapping file:"
echo "   chmod 600 uge_mapping_secure.txt"
echo "   sudo mv uge_mapping_secure.txt /root/secure/"
echo ""
echo "5. Run analysis:"
echo "   python3 analyze_concurrent_load.py"
echo "   python3 analyze_submission_abandonment_events.py"
echo ""
echo "================================================================"
echo ""
