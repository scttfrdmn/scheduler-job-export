#!/bin/bash
#
# Comprehensive LSF Job Data Export with User/Group Information
# Compatible with anonymize_cluster_data.sh and all analysis tools
#
# Equivalent to export_with_users.sh for SLURM
#

set -euo pipefail

# Configuration
START_DATE="${1:-$(date -d '1 year ago' '+%Y/%m/%d' 2>/dev/null || date -v-1y '+%Y/%m/%d')}"
END_DATE="${2:-$(date '+%Y/%m/%d')}"
OUTPUT_FILE="lsf_jobs_with_users_$(date +%Y%m%d).csv"

echo "================================================================"
echo "LSF Comprehensive Job Data Export"
echo "================================================================"
echo ""
echo "Date range: $START_DATE to $END_DATE"
echo "Output file: $OUTPUT_FILE"
echo ""

# Check if bhist is available
if ! command -v bhist &> /dev/null; then
    echo "ERROR: bhist command not found. Is LSF installed?"
    echo ""
    echo "LSF must be installed and LSF_ENVDIR must be set."
    echo "Try: source /path/to/lsf/conf/profile.lsf"
    exit 1
fi

# Check if bacct is available (better for detailed accounting)
HAVE_BACCT=false
if command -v bacct &> /dev/null; then
    HAVE_BACCT=true
    echo "✓ Found bacct (will use for enhanced accounting data)"
fi

echo "Querying LSF accounting database..."
echo "This may take several minutes for large date ranges..."
echo ""

TEMP_FILE=$(mktemp)
BACCT_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE" "$BACCT_FILE"' EXIT

# Export with bhist -l for detailed output
# -C specifies time range
# -a includes all users (requires LSF admin privileges)
echo "Running bhist query..."
bhist -C "$START_DATE,${END_DATE}" -l -a > "$TEMP_FILE" 2>&1 || {
    echo "Warning: bhist -a failed (may need admin privileges)"
    echo "Trying without -a (only your jobs)..."
    bhist -C "$START_DATE,${END_DATE}" -l > "$TEMP_FILE"
}

# If bacct is available, also query it for more detailed resource usage
if [ "$HAVE_BACCT" = true ]; then
    echo "Running bacct query for resource usage..."
    bacct -C "$START_DATE,${END_DATE}" -l > "$BACCT_FILE" 2>&1 || {
        echo "Warning: bacct query failed, will use bhist data only"
        HAVE_BACCT=false
    }
fi

echo ""
echo "Parsing LSF output into standardized CSV format..."

# Parse bhist output into CSV
python3 << 'PYTHON_EOF'
import sys
import csv
import re
from datetime import datetime
from collections import defaultdict

temp_file = sys.argv[1]
bacct_file = sys.argv[2] if len(sys.argv) > 2 else None
output_file = sys.argv[3]
have_bacct = sys.argv[4] == 'true' if len(sys.argv) > 4 else False

# Read bhist -l output
print("Parsing bhist output...", file=sys.stderr)

with open(temp_file, 'r') as f:
    lines = f.readlines()

# Parse records from bhist (separated by blank lines or "Job <jobid>")
records = []
current_record = {}
in_summary = False

for line in lines:
    line = line.rstrip()

    # Skip header/summary lines
    if 'Summary of time in seconds' in line or 'SUMMARY' in line:
        in_summary = True
        continue
    if in_summary and line.startswith('---'):
        in_summary = False
        continue
    if in_summary:
        continue

    # New job record
    if line.startswith('Job <'):
        if current_record and 'job_id' in current_record:
            records.append(current_record)
        current_record = {}

        # Extract job ID from "Job <12345>, Job Name <jobname>, User <username>"
        job_match = re.search(r'Job <(\d+)>', line)
        if job_match:
            current_record['job_id'] = job_match.group(1)

        user_match = re.search(r'User <([^>]+)>', line)
        if user_match:
            current_record['user'] = user_match.group(1)

        name_match = re.search(r'Job Name <([^>]+)>', line)
        if name_match:
            current_record['job_name'] = name_match.group(1)

        continue

    # Skip empty lines
    if not line.strip():
        continue

    # Parse key: value pairs (lines with colons)
    if ':' in line and not line.startswith(' ' * 20):
        colon_pos = line.find(':')
        if colon_pos > 0 and colon_pos < 40:  # Reasonable key length
            key = line[:colon_pos].strip()
            value = line[colon_pos+1:].strip()

            # Map LSF fields to our standard fields
            if key == 'User':
                current_record['user'] = value.split('<')[1].split('>')[0] if '<' in value else value

            elif key == 'User Group':
                current_record['group'] = value

            elif key == 'Project Name':
                current_record['account'] = value

            elif key == 'Job Name':
                current_record['job_name'] = value

            elif key == 'Queue':
                current_record['queue'] = value.split('<')[1].split('>')[0] if '<' in value else value

            elif key == 'Command':
                # Store command for reference
                current_record['command'] = value[:100]  # Truncate long commands

            elif key == 'Processors Requested':
                # Extract number of processors
                match = re.search(r'(\d+)\s+(?:Processor|Task|Core)', value)
                if match:
                    current_record['cpus'] = match.group(1)
                else:
                    # Try to find any number
                    match = re.search(r'(\d+)', value)
                    if match:
                        current_record['cpus'] = match.group(1)

            elif key == 'Requested Resources':
                # Extract memory and other resource requests
                # Format: rusage[mem=8192,duration=1h] span[hosts=1]

                # Memory
                mem_match = re.search(r'mem=(\d+)', value)
                if mem_match:
                    current_record['mem_req'] = mem_match.group(1)

                # Span/hosts
                hosts_match = re.search(r'hosts=(\d+)', value)
                if hosts_match:
                    current_record['nodes'] = hosts_match.group(1)

                span_match = re.search(r'span\[([^\]]+)\]', value)
                if span_match:
                    current_record['span'] = span_match.group(1)

            elif key == 'Execution Home':
                pass  # Not needed for analysis

            elif key == 'Execution CWD':
                pass  # Not needed for analysis

            elif key == 'Execution Hosts':
                # Extract hostnames from format like: <host1>*4 <host2>*2
                hosts = re.findall(r'<([^>]+)>', value)
                if hosts:
                    # Get unique hostnames
                    unique_hosts = list(set(hosts))
                    current_record['nodelist'] = ','.join(unique_hosts)
                    current_record['nodes'] = str(len(unique_hosts))

            elif key in ['Submitted Time', 'Started', 'Dispatched', 'Completed', 'Finish Time']:
                # Parse LSF datetime format
                date_str = value.strip()
                if date_str and date_str != '-' and date_str != 'Not available':
                    try:
                        # Try common LSF formats
                        # "Mon Jan  1 00:00:00 2024"
                        # "Jan  1 00:00 2024"
                        for fmt in ['%b %d %H:%M:%S %Y', '%a %b %d %H:%M:%S %Y',
                                   '%b %d %H:%M %Y', '%Y/%m/%d %H:%M:%S']:
                            try:
                                dt = datetime.strptime(date_str, fmt)
                                iso_time = dt.strftime('%Y-%m-%d %H:%M:%S')

                                if key == 'Submitted Time':
                                    current_record['submit_time'] = iso_time
                                elif key in ['Started', 'Dispatched']:
                                    if 'start_time' not in current_record:
                                        current_record['start_time'] = iso_time
                                elif key in ['Completed', 'Finish Time']:
                                    current_record['end_time'] = iso_time
                                break
                            except ValueError:
                                continue
                    except:
                        pass

            elif key == 'Status':
                # Job status: DONE, EXIT, etc.
                current_record['status'] = value

            elif key == 'Exit Code':
                current_record['exit_status'] = value

# Add last record
if current_record and 'job_id' in current_record:
    records.append(current_record)

print(f"Parsed {len(records)} job records from bhist", file=sys.stderr)

# Optionally merge bacct data if available
if have_bacct and bacct_file:
    print("Parsing bacct output for enhanced resource data...", file=sys.stderr)
    # TODO: Parse bacct output and merge with bhist records
    # bacct has more detailed resource usage info

# Write CSV with standardized columns
fieldnames = [
    'user', 'group', 'account', 'job_id', 'job_name', 'queue',
    'cpus', 'mem_req', 'nodes', 'nodelist', 'submit_time',
    'start_time', 'end_time', 'exit_status', 'status'
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

python3 - "$TEMP_FILE" "$BACCT_FILE" "$OUTPUT_FILE" "$HAVE_BACCT"

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
echo "     lsf_jobs_anonymized.csv \\"
echo "     lsf_mapping_secure.txt"
echo ""
echo "4. Secure the mapping file:"
echo "   chmod 600 lsf_mapping_secure.txt"
echo "   sudo mv lsf_mapping_secure.txt /root/secure/"
echo ""
echo "5. Run analysis:"
echo "   python3 analyze_concurrent_load.py"
echo "   python3 analyze_submission_abandonment_events.py"
echo ""
echo "================================================================"
echo ""
