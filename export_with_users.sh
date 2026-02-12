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

# Load security libraries
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/validation.sh"
source "$SCRIPT_DIR/security_logging.sh"

# Date range configuration (command-line arguments or defaults)
START_DATE="${1:-$(date -d '1 year ago' '+%Y-%m-%d' 2>/dev/null || date -v-1y '+%Y-%m-%d')}"
END_DATE="${2:-$(date '+%Y-%m-%d')}"

# Validate and sanitize date inputs
if ! START_DATE=$(validate_and_sanitize_date "$START_DATE" "slurm"); then
    log_validation_failure "date" "$START_DATE"
    echo "ERROR: Invalid start date format" >&2
    echo "Expected: YYYY-MM-DD (e.g., 2024-01-31)" >&2
    exit 1
fi

if ! END_DATE=$(validate_and_sanitize_date "$END_DATE" "slurm"); then
    log_validation_failure "date" "$END_DATE"
    echo "ERROR: Invalid end date format" >&2
    echo "Expected: YYYY-MM-DD (e.g., 2024-12-31)" >&2
    exit 1
fi

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

# Log export start
log_export_start "SLURM" "start=$START_DATE end=$END_DATE output=$OUTPUT_FILE"

# Export with sacct (pipe-separated output)
echo "Querying SLURM accounting database..."
sacct -a \
  --format=User,Group,Account,JobID,JobName,ReqCPUS,ReqMem,NNodes,NodeList,Submit,Start,End,ExitCode,State,MaxRSS,TotalCPU,Elapsed,AllocCPUS \
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
    'cpus_req', 'mem_req', 'nodes', 'nodelist',
    'submit_time', 'start_time', 'end_time', 'exit_status', 'status',
    'mem_used', 'cpu_time_used', 'walltime_used', 'cpus_alloc'
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
        # Parse memory fields (MaxRSS can be like "1234567K" or "1234M")
        max_rss = fields[14] if len(fields) > 14 else ''
        mem_used_mb = ''
        if max_rss:
            # Parse formats like "1234567K", "1234M", "1G"
            if max_rss.endswith('K'):
                mem_used_mb = str(int(float(max_rss[:-1]) / 1024))
            elif max_rss.endswith('M'):
                mem_used_mb = str(int(float(max_rss[:-1])))
            elif max_rss.endswith('G'):
                mem_used_mb = str(int(float(max_rss[:-1]) * 1024))
            else:
                mem_used_mb = max_rss  # Assume bytes, convert to MB
                try:
                    mem_used_mb = str(int(float(max_rss) / (1024*1024)))
                except:
                    mem_used_mb = ''

        # Parse TotalCPU (format: "days-hours:minutes:seconds" or "hours:minutes:seconds")
        total_cpu = fields[15] if len(fields) > 15 else ''
        cpu_seconds = ''
        if total_cpu:
            try:
                # Handle format like "1-02:03:04" (1 day, 2 hours, 3 min, 4 sec)
                if '-' in total_cpu:
                    days, hms = total_cpu.split('-')
                    h, m, s = hms.split(':')
                    cpu_seconds = str(int(days)*86400 + int(h)*3600 + int(m)*60 + float(s))
                else:
                    # Format like "02:03:04"
                    parts = total_cpu.split(':')
                    if len(parts) == 3:
                        h, m, s = parts
                        cpu_seconds = str(int(h)*3600 + int(m)*60 + float(s))
            except:
                cpu_seconds = ''

        # Parse Elapsed (same format as TotalCPU)
        elapsed = fields[16] if len(fields) > 16 else ''
        walltime_seconds = ''
        if elapsed:
            try:
                if '-' in elapsed:
                    days, hms = elapsed.split('-')
                    h, m, s = hms.split(':')
                    walltime_seconds = str(int(days)*86400 + int(h)*3600 + int(m)*60 + float(s))
                else:
                    parts = elapsed.split(':')
                    if len(parts) == 3:
                        h, m, s = parts
                        walltime_seconds = str(int(h)*3600 + int(m)*60 + float(s))
            except:
                walltime_seconds = ''

        record = {
            'user': fields[0],
            'group': fields[1],
            'account': fields[2],
            'job_id': fields[3],
            'job_name': fields[4] if len(fields) > 4 else '',
            'cpus_req': fields[5] if len(fields) > 5 else '1',
            'mem_req': fields[6] if len(fields) > 6 else '',
            'nodes': fields[7] if len(fields) > 7 else '1',
            'nodelist': fields[8] if len(fields) > 8 else '',
            'submit_time': fields[9] if len(fields) > 9 else '',
            'start_time': fields[10] if len(fields) > 10 else '',
            'end_time': fields[11] if len(fields) > 11 else '',
            'exit_status': fields[12] if len(fields) > 12 else '',
            'status': fields[13] if len(fields) > 13 else '',
            'mem_used': mem_used_mb,
            'cpu_time_used': cpu_seconds,
            'walltime_used': walltime_seconds,
            'cpus_alloc': fields[17] if len(fields) > 17 else ''
        }

        # Set defaults for missing values
        if not record['group']:
            record['group'] = 'unknown'
        if not record['cpus_req']:
            record['cpus_req'] = '1'
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

# Calculate statistics and log completion
TOTAL_JOBS=$(tail -n +2 "$OUTPUT_FILE" | wc -l)
log_export_complete "SLURM" "$TOTAL_JOBS" "$OUTPUT_FILE"

# Generate integrity checksum
generate_checksum "$OUTPUT_FILE"

echo "Statistics:"
echo "  Output file: $OUTPUT_FILE"
echo "  Total jobs: $TOTAL_JOBS"
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
