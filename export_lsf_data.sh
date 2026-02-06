#!/bin/bash
#
# Export IBM Spectrum LSF Job Data with User/Group Information
# Compatible with anonymize_cluster_data.sh
#

set -euo pipefail

# Configuration
START_DATE="${1:-$(date -d '1 year ago' '+%Y/%m/%d')}"  # YYYY/MM/DD format
END_DATE="${2:-$(date '+%Y/%m/%d')}"
OUTPUT_FILE="lsf_jobs_with_users_$(date +%Y%m%d).csv"

echo "Exporting LSF job data with user/group information..."
echo "Date range: $START_DATE to $END_DATE"
echo "Output file: $OUTPUT_FILE"
echo ""

# Check if bhist is available
if ! command -v bhist &> /dev/null; then
    echo "ERROR: bhist command not found. Is LSF installed?"
    exit 1
fi

echo "Querying LSF accounting database (this may take several minutes)..."

# Use bhist to export job history
# -l = long format with all details
# -C = specify time range

TEMP_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE"' EXIT

# Export with bhist
# Note: bhist -l gives detailed output that we'll parse
bhist -C "$START_DATE,${END_DATE}" -l -a > "$TEMP_FILE"

echo "Parsing LSF output into CSV format..."

# Parse bhist output into CSV
python3 << 'PYTHON_EOF'
import sys
import csv
import re
from datetime import datetime

# Read bhist -l output
with open(sys.argv[1], 'r') as f:
    lines = f.readlines()

# Parse records (separated by blank lines or "Job <jobid>")
records = []
current_record = {}

for line in lines:
    line = line.rstrip()

    # New job record
    if line.startswith('Job <'):
        if current_record:
            records.append(current_record)
        current_record = {}
        # Extract job ID
        match = re.search(r'Job <(\d+)>', line)
        if match:
            current_record['job_id'] = match.group(1)
        continue

    # Parse key: value pairs
    if ':' in line and not line.startswith(' ' * 20):
        # Find first colon
        colon_pos = line.find(':')
        if colon_pos > 0:
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
            elif key == 'Processors Requested':
                match = re.search(r'(\d+)', value)
                current_record['cpus'] = match.group(1) if match else '1'
            elif key == 'Requested Resources':
                # Extract memory if present
                mem_match = re.search(r'rusage\[mem=(\d+)\]', value)
                if mem_match:
                    current_record['mem_req'] = mem_match.group(1)
            elif key == 'Execution Home':
                pass  # Not needed
            elif key == 'Execution Hosts':
                # Extract hostnames
                hosts = re.findall(r'<([^>]+)>', value)
                if hosts:
                    current_record['nodelist'] = ','.join(hosts)
                    current_record['nodes'] = str(len(set(hosts)))
            elif key == 'Submitted from host':
                pass  # Not needed
            elif key in ['Submitted Time', 'Started', 'Completed', 'Dispatched']:
                # Parse LSF datetime format
                # Example: "Mon Jan  1 00:00:00 2024"
                try:
                    # LSF uses different formats, try to parse
                    date_str = value.strip()
                    if date_str and date_str != '-':
                        # Try common LSF format
                        try:
                            dt = datetime.strptime(date_str, '%b %d %H:%M:%S %Y')
                            iso_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            try:
                                dt = datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y')
                                iso_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                            except:
                                iso_time = date_str

                        if key == 'Submitted Time':
                            current_record['submit_time'] = iso_time
                        elif key in ['Started', 'Dispatched']:
                            current_record['start_time'] = iso_time
                        elif key == 'Completed':
                            current_record['end_time'] = iso_time
                except:
                    pass

# Add last record
if current_record:
    records.append(current_record)

# Write CSV
fieldnames = [
    'user', 'group', 'account', 'job_id', 'job_name', 'queue',
    'cpus', 'mem_req', 'nodes', 'nodelist', 'submit_time',
    'start_time', 'end_time'
]

with open(sys.argv[2], 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for rec in records:
        # Ensure all fields exist
        row = {k: rec.get(k, '') for k in fieldnames}
        # Set defaults
        if not row['cpus']:
            row['cpus'] = '1'
        if not row['nodes']:
            row['nodes'] = '1'
        writer.writerow(row)

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
echo "     ./anonymize_cluster_data.sh $OUTPUT_FILE lsf_jobs_anonymized.csv mapping_secure.txt"
echo ""
echo "  3. Secure the mapping file:"
echo "     chmod 600 mapping_secure.txt"
echo "     sudo mv mapping_secure.txt /root/secure/"
echo ""
