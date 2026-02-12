#!/bin/bash
#
# Comprehensive PBS/Torque/PBS Pro Job Data Export with User/Group Information
# Compatible with anonymize_cluster_data.sh and all analysis tools
#
# Equivalent to export_with_users.sh for SLURM
#
# Supports: PBS Pro, OpenPBS, Torque
#

set -euo pipefail

# Configuration
START_DATE="${1:-$(date -d '1 year ago' +%Y%m%d 2>/dev/null || date -v-1y +%Y%m%d)}"
END_DATE="${2:-$(date +%Y%m%d)}"
OUTPUT_FILE="pbs_jobs_with_users_$(date +%Y%m%d).csv"

echo "================================================================"
echo "PBS/Torque Comprehensive Job Data Export"
echo "================================================================"
echo ""
echo "Date range: $START_DATE to $END_DATE"
echo "Output file: $OUTPUT_FILE"
echo ""

# Detect PBS variant
PBS_VARIANT="unknown"
if command -v qstat &> /dev/null; then
    # Check version string to determine variant
    VERSION_OUTPUT=$(qstat --version 2>&1 || qstat -B 2>&1 || echo "")
    if echo "$VERSION_OUTPUT" | grep -qi "pbs pro"; then
        PBS_VARIANT="PBS Pro"
    elif echo "$VERSION_OUTPUT" | grep -qi "torque"; then
        PBS_VARIANT="Torque"
    elif echo "$VERSION_OUTPUT" | grep -qi "openpbs"; then
        PBS_VARIANT="OpenPBS"
    else
        PBS_VARIANT="PBS"
    fi
fi

echo "Detected PBS variant: $PBS_VARIANT"
echo ""

# Find accounting directory
ACCT_DIR=""
for dir in \
    "$PBS_HOME/server_priv/accounting" \
    "/var/spool/pbs/server_priv/accounting" \
    "/var/spool/torque/server_priv/accounting" \
    "/opt/pbs/server_priv/accounting" \
    "/usr/spool/pbs/server_priv/accounting"; do
    if [ -d "$dir" ]; then
        ACCT_DIR="$dir"
        break
    fi
done

if [ -z "$ACCT_DIR" ]; then
    echo "ERROR: Cannot find PBS accounting directory"
    echo ""
    echo "Tried:"
    echo "  \$PBS_HOME/server_priv/accounting"
    echo "  /var/spool/pbs/server_priv/accounting"
    echo "  /var/spool/torque/server_priv/accounting"
    echo "  /opt/pbs/server_priv/accounting"
    echo ""
    echo "Please set PBS_HOME or specify accounting directory:"
    echo "  export PBS_HOME=/path/to/pbs"
    echo "  export PBS_ACCT_DIR=/path/to/accounting"
    exit 1
fi

if [ ! -r "$ACCT_DIR" ]; then
    echo "ERROR: Cannot read accounting directory: $ACCT_DIR"
    echo "You may need sudo/root access to read PBS accounting logs"
    exit 1
fi

echo "Using accounting directory: $ACCT_DIR"
echo ""
echo "Finding accounting files in date range..."

# PBS accounting files are named YYYYMMDD
ACCT_FILES=()
for date_file in $(ls "$ACCT_DIR" | grep -E '^[0-9]{8}$' | sort); do
    if [ "$date_file" -ge "$START_DATE" ] && [ "$date_file" -le "$END_DATE" ]; then
        ACCT_FILES+=("$ACCT_DIR/$date_file")
    fi
done

# Also check for compressed files
for date_file in $(ls "$ACCT_DIR" | grep -E '^[0-9]{8}\.(gz|bz2)$' | sed 's/\.(gz|bz2)$//' | sort); do
    if [ "$date_file" -ge "$START_DATE" ] && [ "$date_file" -le "$END_DATE" ]; then
        # Check both .gz and .bz2
        if [ -f "$ACCT_DIR/${date_file}.gz" ]; then
            ACCT_FILES+=("$ACCT_DIR/${date_file}.gz")
        elif [ -f "$ACCT_DIR/${date_file}.bz2" ]; then
            ACCT_FILES+=("$ACCT_DIR/${date_file}.bz2")
        fi
    fi
done

if [ ${#ACCT_FILES[@]} -eq 0 ]; then
    echo "ERROR: No accounting files found in date range $START_DATE to $END_DATE"
    echo ""
    echo "Available files:"
    ls -1 "$ACCT_DIR" | head -20
    exit 1
fi

echo "Found ${#ACCT_FILES[@]} accounting files"
echo ""
echo "Parsing accounting records..."

# Parse PBS accounting logs
python3 << 'PYTHON_EOF'
import sys
import csv
import os
import re
import gzip
import bz2
from datetime import datetime

acct_files = sys.argv[1:-1]
output_file = sys.argv[-1]

print(f"Processing {len(acct_files)} accounting files...", file=sys.stderr)

# PBS accounting format:
# timestamp;record_type;job_id;attribute=value;attribute=value;...
#
# Record types:
# E = End (completed job) - this is what we want
# S = Start
# Q = Queue
# D = Delete
# A = Abort

records = []
files_processed = 0
records_found = 0

for acct_file in acct_files:
    files_processed += 1
    basename = os.path.basename(acct_file)
    if files_processed % 10 == 0:
        print(f"  Processing file {files_processed}/{len(acct_files)}: {basename}", file=sys.stderr)

    # Open file (handle gzip and bz2)
    if acct_file.endswith('.gz'):
        opener = lambda f: gzip.open(f, 'rt')
    elif acct_file.endswith('.bz2'):
        opener = lambda f: bz2.open(f, 'rt')
    else:
        opener = lambda f: open(f, 'r')

    try:
        with opener(acct_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Parse PBS accounting line
                parts = line.split(';')
                if len(parts) < 4:
                    continue

                timestamp_str = parts[0]
                record_type = parts[1]
                job_id = parts[2]

                # We only want 'E' (End) records for completed jobs
                if record_type != 'E':
                    continue

                records_found += 1

                # Parse attributes (key=value pairs)
                attrs = {}
                for i in range(3, len(parts)):
                    if '=' in parts[i]:
                        key, value = parts[i].split('=', 1)
                        attrs[key] = value

                # Convert timestamp (seconds since epoch)
                try:
                    dt = datetime.fromtimestamp(int(timestamp_str))
                    end_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    end_time = ''

                # Extract standard fields
                record = {
                    'user': attrs.get('user', ''),
                    'group': attrs.get('group', ''),
                    'account': attrs.get('account', attrs.get('Account_Name', '')),
                    'job_id': job_id,
                    'job_name': attrs.get('jobname', ''),
                    'queue': attrs.get('queue', ''),
                    'cpus': '',
                    'mem_req': '',
                    'nodes': '',
                    'nodelist': '',
                    'submit_time': '',
                    'start_time': '',
                    'end_time': end_time,
                    'exit_status': attrs.get('Exit_status', ''),
                }

                # Parse resource requests
                # PBS Pro: Resource_List.ncpus, Resource_List.mem, Resource_List.nodect
                # Torque: Resource_List.nodes, Resource_List.mem

                # CPUs REQUESTED
                if 'Resource_List.ncpus' in attrs:
                    record['cpus_req'] = attrs['Resource_List.ncpus']
                elif 'Resource_List.nodes' in attrs:
                    # Torque format: "2:ppn=16" means 2 nodes, 16 procs per node
                    nodes_spec = attrs['Resource_List.nodes']
                    # Parse formats like "2", "2:ppn=16", "1:ppn=4:mem=8gb"
                    match = re.search(r'^(\d+)', nodes_spec)
                    if match:
                        num_nodes = int(match.group(1))
                        record['nodes'] = str(num_nodes)

                    ppn_match = re.search(r'ppn=(\d+)', nodes_spec)
                    if ppn_match:
                        ppn = int(ppn_match.group(1))
                        if record['nodes']:
                            record['cpus_req'] = str(num_nodes * ppn)
                        else:
                            record['cpus_req'] = str(ppn)

                # Memory
                if 'Resource_List.mem' in attrs:
                    mem_str = attrs['Resource_List.mem']
                    # Parse formats: "8gb", "8192mb", "8388608kb"
                    mem_match = re.match(r'(\d+)(gb|mb|kb)?', mem_str.lower())
                    if mem_match:
                        mem_value = int(mem_match.group(1))
                        mem_unit = mem_match.group(2) if mem_match.group(2) else 'mb'

                        # Convert to MB
                        if mem_unit == 'gb':
                            mem_mb = mem_value * 1024
                        elif mem_unit == 'kb':
                            mem_mb = mem_value // 1024
                        else:  # mb
                            mem_mb = mem_value

                        record['mem_req'] = str(mem_mb)

                # Nodes count
                if 'Resource_List.nodect' in attrs:
                    record['nodes'] = attrs['Resource_List.nodect']
                elif not record['nodes']:
                    record['nodes'] = '1'

                # Execution hosts
                if 'exec_host' in attrs:
                    exec_host = attrs['exec_host']
                    # Format: "node1/0+node1/1+node2/0" or "node1/0*2+node2/0*4"
                    # Extract unique node names
                    nodes = re.findall(r'([^/+*]+)/', exec_host)
                    if nodes:
                        unique_nodes = list(set(nodes))
                        record['nodelist'] = ','.join(unique_nodes)
                        if not record['nodes']:
                            record['nodes'] = str(len(unique_nodes))

                # Submit time (ctime = creation time)
                if 'ctime' in attrs:
                    try:
                        dt = datetime.fromtimestamp(int(attrs['ctime']))
                        record['submit_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                # Start time
                if 'start' in attrs:
                    try:
                        dt = datetime.fromtimestamp(int(attrs['start']))
                        record['start_time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        pass

                # Resource usage (actual consumption)
                if 'resources_used.mem' in attrs:
                    mem_str = attrs['resources_used.mem']
                    mem_match = re.match(r'(\d+)(gb|mb|kb)?', mem_str.lower())
                    if mem_match:
                        mem_value = int(mem_match.group(1))
                        mem_unit = mem_match.group(2) if mem_match.group(2) else 'kb'
                        if mem_unit == 'gb':
                            mem_mb = mem_value * 1024
                        elif mem_unit == 'kb':
                            mem_mb = mem_value // 1024
                        else:
                            mem_mb = mem_value
                        record['mem_used'] = str(mem_mb)

                if 'resources_used.cput' in attrs:
                    cput_str = attrs['resources_used.cput']
                    parts = cput_str.split(':')
                    if len(parts) == 3:
                        try:
                            h, m, s = parts
                            record['cpu_time_used'] = str(int(h)*3600 + int(m)*60 + int(s))
                        except:
                            pass

                if 'resources_used.walltime' in attrs:
                    wall_str = attrs['resources_used.walltime']
                    parts = wall_str.split(':')
                    if len(parts) == 3:
                        try:
                            h, m, s = parts
                            record['walltime_used'] = str(int(h)*3600 + int(m)*60 + int(s))
                        except:
                            pass

                # Defaults
                if not record['cpus_req']:
                    record['cpus_req'] = '1'

                records.append(record)

    except Exception as e:
        print(f"Warning: Error processing {basename}: {e}", file=sys.stderr)
        continue

print(f"\nParsed {records_found} job records from {files_processed} files", file=sys.stderr)

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

# Print statistics
print("\n" + "="*80, file=sys.stderr)
print("EXPORT STATISTICS", file=sys.stderr)
print("="*80, file=sys.stderr)

unique_users = len(set(r['user'] for r in records if r['user']))
unique_groups = len(set(r['group'] for r in records if r['group']))
unique_queues = len(set(r['queue'] for r in records if r['queue']))

print(f"\nJobs exported: {len(records):,}", file=sys.stderr)
print(f"Unique users: {unique_users:,}", file=sys.stderr)
print(f"Unique groups: {unique_groups:,}", file=sys.stderr)
print(f"Unique queues: {unique_queues:,}", file=sys.stderr)

# Date range
dates_with_jobs = [r['submit_time'] for r in records if r['submit_time']]
if dates_with_jobs:
    min_date = min(dates_with_jobs)
    max_date = max(dates_with_jobs)
    print(f"Date range: {min_date[:10]} to {max_date[:10]}", file=sys.stderr)

print(file=sys.stderr)
PYTHON_EOF

python3 - "${ACCT_FILES[@]}" "$OUTPUT_FILE"

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
echo "     pbs_jobs_anonymized.csv \\"
echo "     pbs_mapping_secure.txt"
echo ""
echo "4. Secure the mapping file:"
echo "   chmod 600 pbs_mapping_secure.txt"
echo "   sudo mv pbs_mapping_secure.txt /root/secure/"
echo ""
echo "5. Run analysis:"
echo "   python3 analyze_concurrent_load.py"
echo "   python3 analyze_submission_abandonment_events.py"
echo ""
echo "================================================================"
echo ""
