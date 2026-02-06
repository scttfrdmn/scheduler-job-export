#!/bin/bash
#
# Export UGE/SGE/OGE Job Data with User/Group Information
# Compatible with anonymize_cluster_data.sh
#
# UGE = Univa Grid Engine
# SGE = Sun Grid Engine
# OGE = Open Grid Engine
#

set -euo pipefail

# Configuration
START_DATE="${1:-01/01/2024}"  # MM/DD/YYYY format for qacct
END_DATE="${2:-$(date +%m/%d/%Y)}"
OUTPUT_FILE="uge_jobs_with_users_$(date +%Y%m%d).csv"

echo "Exporting UGE/SGE job data with user/group information..."
echo "Date range: $START_DATE to $END_DATE"
echo "Output file: $OUTPUT_FILE"
echo ""

# Check if qacct is available
if ! command -v qacct &> /dev/null; then
    echo "ERROR: qacct command not found. Is UGE/SGE installed?"
    exit 1
fi

echo "Querying accounting database (this may take several minutes)..."

# Export using qacct
# Format: qacct -j -b start_time -e end_time
# Output is text format, we'll parse it into CSV

TEMP_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE"' EXIT

qacct -b "$START_DATE" -e "$END_DATE" > "$TEMP_FILE"

echo "Parsing accounting data into CSV format..."

# Parse qacct output into CSV
python3 << 'PYTHON_EOF'
import sys
import csv
from datetime import datetime

# Read qacct output
with open(sys.argv[1], 'r') as f:
    lines = f.readlines()

# Parse records (separated by ============)
records = []
current_record = {}

for line in lines:
    line = line.strip()

    # New record separator
    if line.startswith('===='):
        if current_record:
            records.append(current_record)
            current_record = {}
        continue

    # Parse key-value pairs
    if line and not line.startswith('#'):
        parts = line.split(None, 1)
        if len(parts) == 2:
            key, value = parts
            current_record[key] = value.strip()

# Add last record
if current_record:
    records.append(current_record)

# Write CSV
fieldnames = [
    'user', 'group', 'account', 'job_id', 'job_name', 'queue',
    'slots', 'mem_req', 'nodes', 'nodelist', 'submit_time',
    'start_time', 'end_time', 'exit_status'
]

with open(sys.argv[2], 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for rec in records:
        # Parse UGE fields into our standard format
        try:
            # Convert UGE date format to ISO
            def parse_uge_date(date_str):
                if not date_str or date_str == '-':
                    return ''
                # UGE format: "Mon Jan  1 00:00:00 2024"
                try:
                    dt = datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y')
                    return dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    return date_str

            row = {
                'user': rec.get('owner', ''),
                'group': rec.get('group', ''),
                'account': rec.get('project', rec.get('department', '')),
                'job_id': rec.get('jobnumber', ''),
                'job_name': rec.get('jobname', ''),
                'queue': rec.get('qname', ''),
                'slots': rec.get('slots', '1'),  # CPUs/cores
                'mem_req': rec.get('maxvmem', rec.get('ru_maxrss', '')),
                'nodes': '1',  # UGE doesn't always track nodes explicitly
                'nodelist': rec.get('hostname', ''),
                'submit_time': parse_uge_date(rec.get('qsub_time', '')),
                'start_time': parse_uge_date(rec.get('start_time', '')),
                'end_time': parse_uge_date(rec.get('end_time', '')),
                'exit_status': rec.get('exit_status', ''),
            }
            writer.writerow(row)
        except Exception as e:
            print(f"Warning: Error parsing record: {e}", file=sys.stderr)
            continue

print(f"Parsed {len(records)} job records", file=sys.stderr)
PYTHON_EOF

python3 - "$TEMP_FILE" "$OUTPUT_FILE"

echo ""
echo "Export complete!"
echo ""
echo "Statistics:"
echo "  Total records: $(tail -n +2 "$OUTPUT_FILE" | wc -l)"
echo "  Output file: $OUTPUT_FILE"
echo ""
echo "Next steps:"
echo "  1. Verify the export:"
echo "     head $OUTPUT_FILE"
echo ""
echo "  2. Run anonymization:"
echo "     ./anonymize_cluster_data.sh $OUTPUT_FILE uge_jobs_anonymized.csv mapping_secure.txt"
echo ""
echo "  3. Secure the mapping file:"
echo "     chmod 600 mapping_secure.txt"
echo "     sudo mv mapping_secure.txt /root/secure/"
echo ""
