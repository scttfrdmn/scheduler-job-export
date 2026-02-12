#!/bin/bash
#
# Export SLURM job data WITH user/group information
# Compatible with anonymize_cluster_data.sh and all analysis tools
#
# Usage: ./export_with_users.sh [START_DATE] [END_DATE]
#   START_DATE: YYYY-MM-DD (default: 1 year ago)
#   END_DATE:   YYYY-MM-DD (default: today)
#
# Examples:
#   ./export_with_users.sh                        # Last year
#   ./export_with_users.sh 2024-01-01 2024-12-31 # Full year 2024
#   ./export_with_users.sh 2024-10-01 2024-10-31 # October 2024
#

set -euo pipefail

# Date range configuration (command-line arguments or defaults)
START_DATE="${1:-$(date -d '1 year ago' '+%Y-%m-%d' 2>/dev/null || date -v-1y '+%Y-%m-%d')}"
END_DATE="${2:-$(date '+%Y-%m-%d')}"

# Output filename with timestamp
OUTPUT_FILE="slurm_jobs_with_users_$(date +%Y%m%d).csv"
TEMP_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE"' EXIT

echo "================================================================"
echo "SLURM Job Data Export with User Information"
echo "================================================================"
echo ""
echo "Date range: $START_DATE to $END_DATE"
echo "Output file: $OUTPUT_FILE"
echo ""

# Export with sacct (pipe-separated output)
echo "Querying SLURM accounting database..."
sacct -a \
  --format=User,Group,Account,JobID,JobName,ReqCPUS,ReqMem,NNodes,NodeList,Submit,Start,End,ExitCode,State \
  --starttime "$START_DATE" \
  --endtime "$END_DATE" \
  --parsable2 \
  > "$TEMP_FILE"

echo "Converting to standardized CSV format..."

# Convert pipe-separated sacct output to standardized comma-separated CSV
python3 << 'PYTHON_EOF'
import sys
import csv
import re

temp_file = sys.argv[1]
output_file = sys.argv[2]

with open(temp_file, 'r') as infile:
    # Read sacct output (pipe-separated)
    lines = infile.readlines()

# Parse header and data
header = lines[0].strip().split('|')
data_lines = lines[1:]

# Standardized fieldnames matching LSF/PBS/UGE format
fieldnames = [
    'user', 'group', 'account', 'job_id', 'job_name',
    'cpus', 'mem_req', 'nodes', 'nodelist',
    'submit_time', 'start_time', 'end_time', 'exit_status', 'status'
]

with open(output_file, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for line in data_lines:
        if not line.strip():
            continue

        fields = line.strip().split('|')
        if len(fields) < len(header):
            continue

        # Map sacct fields to standardized names
        record = {
            'user': fields[0],
            'group': fields[1],
            'account': fields[2],
            'job_id': fields[3],
            'job_name': fields[4] if len(fields) > 4 else '',
            'cpus': fields[5] if len(fields) > 5 else '1',
            'mem_req': fields[6] if len(fields) > 6 else '',
            'nodes': fields[7] if len(fields) > 7 else '1',
            'nodelist': fields[8] if len(fields) > 8 else '',
            'submit_time': fields[9] if len(fields) > 9 else '',
            'start_time': fields[10] if len(fields) > 10 else '',
            'end_time': fields[11] if len(fields) > 11 else '',
            'exit_status': fields[12] if len(fields) > 12 else '',
            'status': fields[13] if len(fields) > 13 else ''
        }

        # Set defaults for missing values
        if not record['group']:
            record['group'] = 'unknown'
        if not record['cpus']:
            record['cpus'] = '1'
        if not record['nodes']:
            record['nodes'] = '1'

        writer.writerow(record)

print(f"Export complete: {output_file}", file=sys.stderr)

PYTHON_EOF

python3 - "$TEMP_FILE" "$OUTPUT_FILE" << 'PYTHON_EOF'
import sys
import csv
import re

temp_file = sys.argv[1]
output_file = sys.argv[2]

with open(temp_file, 'r') as infile:
    lines = infile.readlines()

header = lines[0].strip().split('|')
data_lines = lines[1:]

fieldnames = [
    'user', 'group', 'account', 'job_id', 'job_name',
    'cpus', 'mem_req', 'nodes', 'nodelist',
    'submit_time', 'start_time', 'end_time', 'exit_status', 'status'
]

records = []
for line in data_lines:
    if not line.strip():
        continue
    fields = line.strip().split('|')
    if len(fields) < 7:
        continue

    record = {
        'user': fields[0],
        'group': fields[1] if fields[1] else 'unknown',
        'account': fields[2],
        'job_id': fields[3],
        'job_name': fields[4] if len(fields) > 4 else '',
        'cpus': fields[5] if len(fields) > 5 and fields[5] else '1',
        'mem_req': fields[6] if len(fields) > 6 else '',
        'nodes': fields[7] if len(fields) > 7 and fields[7] else '1',
        'nodelist': fields[8] if len(fields) > 8 else '',
        'submit_time': fields[9] if len(fields) > 9 else '',
        'start_time': fields[10] if len(fields) > 10 else '',
        'end_time': fields[11] if len(fields) > 11 else '',
        'exit_status': fields[12] if len(fields) > 12 else '',
        'status': fields[13] if len(fields) > 13 else ''
    }
    records.append(record)

with open(output_file, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

print(f"Wrote {len(records)} records to {output_file}", file=sys.stderr)

PYTHON_EOF

echo ""
echo "================================================================"
echo "Export complete!"
echo "================================================================"
echo ""
echo "Statistics:"
echo "  Output file: $OUTPUT_FILE"
echo "  Total jobs: $(tail -n +2 "$OUTPUT_FILE" | wc -l)"
echo ""
echo "Next steps:"
echo "  1. Verify the export looks correct:"
echo "     head $OUTPUT_FILE"
echo ""
echo "  2. Run anonymization:"
echo "     ./anonymize_cluster_data.sh $OUTPUT_FILE slurm_anonymized.csv mapping_secure.txt"
echo ""
echo "  3. Secure the mapping file:"
echo "     chmod 600 mapping_secure.txt"
echo ""
