#!/bin/bash
#
# Export SLURM job data WITH user/group information
# This matches your existing oscar_all_jobs_2025.csv schema + adds user/group fields
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

echo "Exporting SLURM job data with user/group information..."
echo "Date range: $START_DATE to $END_DATE"
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
  --starttime "$START_DATE" \
  --endtime "$END_DATE" \
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
