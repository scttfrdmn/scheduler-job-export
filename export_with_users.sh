#!/bin/bash
#
# Export SLURM job data WITH user/group information
# This matches your existing oscar_all_jobs_2025.csv schema + adds user/group fields
#

set -euo pipefail

# Output filename with timestamp
OUTPUT_FILE="oscar_jobs_with_users_$(date +%Y%m%d).csv"

echo "Exporting SLURM job data with user/group information..."
echo "Output file: $OUTPUT_FILE"
echo ""

# Export with ALL fields you need:
# - User identification: User, Account, Group
# - CPU/Memory: ReqCPUS (cpus_req), ReqMem (mem_req)
# - Nodes: NNodes (nodes_alloc), NodeList (nodelist)
# - Resources: AllocTRES (tres_alloc), ReqGRES (gres_used)
# - Timing: Submit (submit_time), Start (start_time), End (end_time)

sacct -a \
  --format=User,Account,Group,ReqCPUS,ReqMem,NNodes,NodeList,AllocTRES,ReqGRES,Submit,Start,End \
  --starttime 2024-01-01 \
  --parsable2 \
  > "$OUTPUT_FILE"

echo "Export complete!"
echo ""
echo "Statistics:"
echo "  Total lines: $(wc -l < "$OUTPUT_FILE")"
echo "  Total jobs: $(tail -n +2 "$OUTPUT_FILE" | wc -l)"
echo ""
echo "Next steps:"
echo "  1. Verify the export looks correct:"
echo "     head $OUTPUT_FILE"
echo ""
echo "  2. Run anonymization:"
echo "     ./anonymize_cluster_data.sh $OUTPUT_FILE oscar_jobs_anonymized.csv mapping_secure.txt"
echo ""
echo "  3. Secure the mapping file:"
echo "     chmod 600 mapping_secure.txt"
echo "     sudo mv mapping_secure.txt /root/secure/"
echo ""
