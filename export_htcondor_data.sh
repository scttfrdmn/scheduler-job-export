#!/bin/bash
#
# Export HTCondor Job Data with User/Group Information
# Compatible with anonymize_cluster_data.sh
#

set -euo pipefail

# Configuration
DAYS_AGO="${1:-365}"  # How many days back to query
OUTPUT_FILE="htcondor_jobs_with_users_$(date +%Y%m%d).csv"

echo "Exporting HTCondor job data with user/group information..."
echo "Querying last $DAYS_AGO days"
echo "Output file: $OUTPUT_FILE"
echo ""

# Check if condor_history is available
if ! command -v condor_history &> /dev/null; then
    echo "ERROR: condor_history command not found. Is HTCondor installed?"
    exit 1
fi

echo "Querying HTCondor history (this may take several minutes)..."

# Use condor_history to export job history
# -long format gives all attributes
# We'll convert to CSV

TEMP_FILE=$(mktemp)
trap 'rm -f "$TEMP_FILE"' EXIT

# Export with condor_history
# -constraint 'JobStatus == 4' means completed jobs
# Add -file option if using file-based history

condor_history -constraint "CompletionDate > (time() - ($DAYS_AGO * 86400))" \
    -af:ht \
    Owner \
    AcctGroup \
    AccountingGroup \
    ClusterId \
    ProcId \
    JobStatus \
    JobPrio \
    RequestCpus \
    RequestMemory \
    NumJobStarts \
    LastRemoteHost \
    QDate \
    JobStartDate \
    CompletionDate \
    ExitCode \
    MemoryUsage \
    RemoteSysCpu \
    RemoteUserCpu \
    RemoteWallClockTime \
    CumulativeRemoteSysCpu \
    CumulativeRemoteUserCpu \
    > "$TEMP_FILE"

echo "Parsing HTCondor output into CSV format..."

# Parse condor_history output into CSV
python3 << 'PYTHON_EOF'
import sys
import csv
from datetime import datetime

# Read condor_history tab-separated output
records = []

with open(sys.argv[1], 'r') as f:
    # First line is header
    header = f.readline().strip().split('\t')

    for line in f:
        line = line.strip()
        if not line:
            continue

        values = line.split('\t')
        if len(values) != len(header):
            continue

        rec = dict(zip(header, values))

        # Convert HTCondor epoch timestamps to ISO format
        def convert_time(ts_str):
            if not ts_str or ts_str == 'undefined':
                return ''
            try:
                # HTCondor uses Unix epoch
                ts = int(float(ts_str))
                dt = datetime.fromtimestamp(ts)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return ts_str

        # Map HTCondor JobStatus integer to string
        def map_job_status(status_code):
            """
            Convert HTCondor JobStatus code to human-readable string.
            1=Idle, 2=Running, 3=Removed, 4=Completed, 5=Held, 6=Transferring, 7=Suspended
            """
            status_map = {
                '1': 'IDLE',
                '2': 'RUNNING',
                '3': 'REMOVED',
                '4': 'COMPLETED',
                '5': 'HELD',
                '6': 'TRANSFERRING',
                '7': 'SUSPENDED'
            }
            return status_map.get(status_code, status_code)

        # Parse AcctGroup or AccountingGroup for group info
        # Format is usually "group_name.username"
        acct_group = rec.get('AcctGroup', rec.get('AccountingGroup', ''))
        group = ''
        if acct_group and '.' in acct_group:
            group = acct_group.split('.')[0]

        # Extract hostname from LastRemoteHost
        # Format: "slot1@hostname.domain"
        # Note: for multi-slot jobs, HTCondor history only records the last host
        nodelist = rec.get('LastRemoteHost', '')
        if '@' in nodelist:
            nodelist = nodelist.split('@')[1].split(':')[0]

        # Calculate actual resource usage
        # MemoryUsage is in MB (HTCondor ClassAd standard unit)
        mem_used = rec.get('MemoryUsage', '')

        # CPU time used - use cumulative fields to handle job restarts correctly
        # CumulativeRemoteSysCpu/UserCpu accumulate across all executions
        # RemoteSysCpu/UserCpu only reflect the last execution
        cpu_time_used = ''
        cum_sys = rec.get('CumulativeRemoteSysCpu', '')
        cum_user = rec.get('CumulativeRemoteUserCpu', '')
        if cum_sys and cum_sys not in ('undefined', '0') and cum_user and cum_user not in ('undefined',):
            try:
                cpu_seconds = float(cum_sys) + float(cum_user)
                cpu_time_used = str(int(cpu_seconds))
            except:
                pass
        if not cpu_time_used:
            # Fall back to non-cumulative (equivalent when NumJobStarts == 1)
            sys_cpu = rec.get('RemoteSysCpu', '0')
            user_cpu = rec.get('RemoteUserCpu', '0')
            try:
                cpu_seconds = float(sys_cpu) + float(user_cpu)
                cpu_time_used = str(int(cpu_seconds))
            except:
                pass

        # Walltime used - prefer RemoteWallClockTime (cumulative across all restarts)
        # CompletionDate - JobStartDate only covers the last execution
        walltime_used = ''
        remote_wall = rec.get('RemoteWallClockTime', '')
        if remote_wall and remote_wall not in ('undefined', '0'):
            try:
                walltime_used = str(int(float(remote_wall)))
            except:
                pass
        if not walltime_used:
            # Fall back to last-execution duration
            try:
                start_ts = int(float(rec.get('JobStartDate', '0')))
                end_ts = int(float(rec.get('CompletionDate', '0')))
                if start_ts > 0 and end_ts > 0:
                    walltime_used = str(end_ts - start_ts)
            except:
                pass

        # Map job status code to string
        job_status_code = rec.get('JobStatus', '')
        status = map_job_status(job_status_code)

        # Get priority value
        priority = rec.get('JobPrio', '')

        record = {
            'user': rec.get('Owner', ''),
            'group': group,
            'account': acct_group,
            'job_id': f"{rec.get('ClusterId', '')}.{rec.get('ProcId', '')}",
            'job_name': '',  # HTCondor doesn't have job name in history by default
            'queue': '',  # HTCondor doesn't use queues in same way
            'cpus_req': rec.get('RequestCpus', '1'),
            'mem_req': rec.get('RequestMemory', ''),  # In MB
            'nodes': '1',  # HTCondor jobs typically run on single node
            'nodelist': nodelist,
            'submit_time': convert_time(rec.get('QDate', '')),
            'start_time': convert_time(rec.get('JobStartDate', '')),
            'end_time': convert_time(rec.get('CompletionDate', '')),
            'exit_status': rec.get('ExitCode', ''),
            'status': status,
            'mem_used': mem_used,
            'cpu_time_used': cpu_time_used,
            'walltime_used': walltime_used,
            'priority': priority,
        }
        records.append(record)

print(f"Parsed {len(records)} job records", file=sys.stderr)

# Write CSV
fieldnames = [
    'user', 'group', 'account', 'job_id', 'job_name', 'queue',
    'cpus_req', 'mem_req', 'nodes', 'nodelist', 'submit_time',
    'start_time', 'end_time', 'exit_status', 'status', 'mem_used',
    'cpu_time_used', 'walltime_used', 'priority'
]

with open(sys.argv[2], 'w', newline='') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)

print(f"Wrote {len(records)} records to {sys.argv[2]}", file=sys.stderr)
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
echo "     ./anonymize_cluster_data.sh $OUTPUT_FILE htcondor_jobs_anonymized.csv mapping_secure.txt"
echo ""
echo "  3. Secure the mapping file:"
echo "     chmod 600 mapping_secure.txt"
echo "     sudo mv mapping_secure.txt /root/secure/"
echo ""
