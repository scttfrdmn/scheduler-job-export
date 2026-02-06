#!/bin/bash
#
# Export PBS/Torque/PBS Pro Job Data with User/Group Information
# Compatible with anonymize_cluster_data.sh
#
# Works with: PBS Pro, OpenPBS, Torque
#

set -euo pipefail

# Configuration
START_DATE="${1:-$(date -d '1 year ago' +%Y%m%d)}"  # YYYYMMDD format
END_DATE="${2:-$(date +%Y%m%d)}"
OUTPUT_FILE="pbs_jobs_with_users_$(date +%Y%m%d).csv"

echo "Exporting PBS/Torque job data with user/group information..."
echo "Date range: $START_DATE to $END_DATE"
echo "Output file: $OUTPUT_FILE"
echo ""

# Check which PBS command is available
PBS_CMD=""
if command -v tracejob &> /dev/null; then
    PBS_CMD="tracejob"
    echo "Using PBS Pro/OpenPBS (tracejob)"
elif command -v qstat &> /dev/null; then
    PBS_CMD="qstat"
    echo "Using PBS/Torque (qstat)"
else
    echo "ERROR: No PBS commands found (tracejob, qstat)"
    exit 1
fi

echo "Reading accounting logs..."

# PBS/Torque accounting logs are typically in /var/spool/pbs/server_priv/accounting/
# PBS Pro logs are in /var/spool/pbs/server_logs/

ACCT_DIR="/var/spool/pbs/server_priv/accounting"
if [ ! -d "$ACCT_DIR" ]; then
    ACCT_DIR="/var/spool/pbs/server_logs"
fi

if [ ! -d "$ACCT_DIR" ]; then
    echo "ERROR: Cannot find PBS accounting directory"
    echo "Tried: /var/spool/pbs/server_priv/accounting"
    echo "       /var/spool/pbs/server_logs"
    echo ""
    echo "Please specify accounting directory:"
    echo "  export PBS_ACCT_DIR=/path/to/accounting"
    exit 1
fi

# Parse accounting logs
python3 << 'PYTHON_EOF'
import sys
import csv
import os
import re
from datetime import datetime
from glob import glob

acct_dir = sys.argv[1]
start_date = sys.argv[2]
end_date = sys.argv[3]
output_file = sys.argv[4]

# Find accounting files in date range
# PBS accounting files: YYYYMMDD or YYYYMMDD.gz
acct_files = []
for f in sorted(glob(os.path.join(acct_dir, '*'))):
    basename = os.path.basename(f).replace('.gz', '')
    # Check if filename is a date
    if re.match(r'^\d{8}$', basename):
        if start_date <= basename <= end_date:
            acct_files.append(f)

print(f"Found {len(acct_files)} accounting files", file=sys.stderr)

# Parse PBS accounting format
# Format: timestamp;record_type;job_id;key=value;key=value;...
records = []

for acct_file in acct_files:
    print(f"Processing {os.path.basename(acct_file)}...", file=sys.stderr)

    # Handle gzipped files
    if acct_file.endswith('.gz'):
        import gzip
        opener = gzip.open
    else:
        opener = open

    with opener(acct_file, 'rt') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split(';')
            if len(parts) < 4:
                continue

            timestamp, record_type, job_id = parts[0:3]

            # We want 'E' (End) records for completed jobs
            if record_type != 'E':
                continue

            # Parse key=value pairs
            attrs = {}
            for i in range(3, len(parts)):
                if '=' in parts[i]:
                    key, value = parts[i].split('=', 1)
                    attrs[key] = value

            # Convert timestamp (seconds since epoch)
            try:
                dt = datetime.fromtimestamp(int(timestamp))
                end_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                end_time = ''

            # Extract job info
            record = {
                'user': attrs.get('user', ''),
                'group': attrs.get('group', ''),
                'account': attrs.get('account', attrs.get('Account_Name', '')),
                'job_id': job_id,
                'job_name': attrs.get('jobname', ''),
                'queue': attrs.get('queue', ''),
                'cpus': attrs.get('Resource_List.ncpus',
                        attrs.get('Resource_List.nodes', '1')),
                'mem_req': attrs.get('Resource_List.mem', ''),
                'nodes': attrs.get('Resource_List.nodect', '1'),
                'nodelist': attrs.get('exec_host', ''),
                'submit_time': '',  # Parse from ctime if available
                'start_time': '',   # Parse from start if available
                'end_time': end_time,
                'exit_status': attrs.get('Exit_status', ''),
            }

            # Parse submit time (ctime)
            if 'ctime' in attrs:
                try:
                    dt = datetime.fromtimestamp(int(attrs['ctime']))
                    record['submit_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            # Parse start time
            if 'start' in attrs:
                try:
                    dt = datetime.fromtimestamp(int(attrs['start']))
                    record['start_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass

            records.append(record)

print(f"Parsed {len(records)} job records", file=sys.stderr)

# Write CSV
fieldnames = [
    'user', 'group', 'account', 'job_id', 'job_name', 'queue',
    'cpus', 'mem_req', 'nodes', 'nodelist', 'submit_time',
    'start_time', 'end_time', 'exit_status'
]

with open(output_file, 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

print(f"Wrote {len(records)} records to {output_file}", file=sys.stderr)
PYTHON_EOF

python3 - "$ACCT_DIR" "$START_DATE" "$END_DATE" "$OUTPUT_FILE"

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
echo "     ./anonymize_cluster_data.sh $OUTPUT_FILE pbs_jobs_anonymized.csv mapping_secure.txt"
echo ""
echo "  3. Secure the mapping file:"
echo "     chmod 600 mapping_secure.txt"
echo "     sudo mv mapping_secure.txt /root/secure/"
echo ""
