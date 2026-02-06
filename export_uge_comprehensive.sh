#!/bin/bash
#
# Comprehensive UGE/SGE/OGE Job Data Export with User/Group Information
# Compatible with anonymize_cluster_data.sh and all analysis tools
#
# Equivalent to export_with_users.sh for SLURM
#
# Supports: Univa Grid Engine (UGE), Sun Grid Engine (SGE), Open Grid Engine (OGE)
#

set -euo pipefail

# Configuration
START_DATE="${1:-01/01/$(date -d '1 year ago' +%Y 2>/dev/null || date -v-1y +%Y)}"
END_DATE="${2:-$(date +%m/%d/%Y)}"
OUTPUT_FILE="uge_jobs_with_users_$(date +%Y%m%d).csv"

echo "================================================================"
echo "UGE/SGE Comprehensive Job Data Export"
echo "================================================================"
echo ""
echo "Date range: $START_DATE to $END_DATE"
echo "Output file: $OUTPUT_FILE"
echo ""

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

echo "Querying accounting database with qacct..."
echo "This may take several minutes for large date ranges..."
echo ""

TEMP_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE"' EXIT

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

with open(sys.argv[1], 'r') as f:
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
                current_record['nodes'] = '1'  # UGE jobs typically single node

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
                current_record['cpus'] = value

            elif key == 'pe_taskid':
                # Parallel environment task ID
                if value != 'undefined':
                    current_record['pe_tasks'] = value

            elif key == 'maxvmem':
                # Maximum virtual memory used
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

                    current_record['mem_req'] = str(mem_mb)

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

print(f"Parsed {len(records)} job records from qacct", file=sys.stderr)

# Write CSV with standardized columns
fieldnames = [
    'user', 'group', 'account', 'job_id', 'job_name', 'queue',
    'cpus', 'mem_req', 'nodes', 'nodelist', 'submit_time',
    'start_time', 'end_time', 'exit_status'
]

output_records = []
for rec in records:
    # Ensure all fields exist with defaults
    row = {k: rec.get(k, '') for k in fieldnames}

    # Set reasonable defaults
    if not row['cpus']:
        row['cpus'] = '1'
    if not row['nodes']:
        row['nodes'] = '1'
    if not row['group']:
        row['group'] = 'unknown'

    output_records.append(row)

with open(sys.argv[2], 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output_records)

print(f"Wrote {len(output_records)} records to {sys.argv[2]}", file=sys.stderr)

# Print statistics
print("\n" + "="*80, file=sys.stderr)
print("EXPORT STATISTICS", file=sys.stderr)
print("="*80, file=sys.stderr)

unique_users = len(set(r['user'] for r in output_records if r['user']))
unique_groups = len(set(r['group'] for r in output_records if r['group']))
unique_queues = len(set(r['queue'] for r in output_records if r['queue']))

print(f"\nJobs exported: {len(output_records):,}", file=sys.stderr)
print(f"Unique users: {unique_users:,}", file=sys.stderr)
print(f"Unique groups: {unique_groups:,}", file=sys.stderr)
print(f"Unique queues: {unique_queues:,}", file=sys.stderr)

# Date range
dates_with_jobs = [r['submit_time'] for r in output_records if r['submit_time']]
if dates_with_jobs:
    min_date = min(dates_with_jobs)
    max_date = max(dates_with_jobs)
    print(f"Date range: {min_date[:10]} to {max_date[:10]}", file=sys.stderr)

print(file=sys.stderr)
PYTHON_EOF

python3 - "$TEMP_FILE" "$OUTPUT_FILE"

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
