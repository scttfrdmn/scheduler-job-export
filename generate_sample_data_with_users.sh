#!/bin/bash
#
# Generate Sample Job Data with User/Group Information
#
# This script creates a sample CSV file with user and group information
# for testing the anonymization script.
#

OUTPUT_FILE="${1:-sample_jobs_with_users.csv}"
NUM_JOBS="${2:-1000}"

echo "Generating $NUM_JOBS sample jobs with user information..."

# Sample users
USERS=(
    "jsmith" "mjones" "alee" "bwilson" "cgarcia"
    "dmartinez" "erobinson" "fclark" "grodriguez" "hlewis"
    "iwalker" "jhall" "kallen" "lyoung" "mking"
    "nwright" "olopez" "phill" "qscott" "radams"
)

# Sample groups
GROUPS=(
    "physics" "biology" "chemistry" "engineering" "mathematics"
    "computer_science" "astronomy" "geology" "environmental" "medical"
)

# Sample nodes
NODES=(
    "node1317" "node1318" "node1319" "node2334" "node2333"
    "node2336" "node2340" "node2343" "node2345" "node2348"
    "gpu2001" "gpu2003" "gpu2004" "gpu2005" "gpu2803"
)

# Write header (matching SLURM sacct format)
cat > "$OUTPUT_FILE" << 'EOF'
user,group,account,cpus_req,mem_req,nodes_alloc,nodelist,tres_alloc,submit_time,start_time,end_time
EOF

# Generate random jobs
for i in $(seq 1 $NUM_JOBS); do
    # Random user and group
    user=${USERS[$RANDOM % ${#USERS[@]}]}
    group=${GROUPS[$RANDOM % ${#GROUPS[@]}]}
    account=$group  # Account often matches group

    # Random job characteristics
    cpus=$((RANDOM % 32 + 1))
    mem=$((cpus * 4096 + RANDOM % 10240))
    nodes=1
    node=${NODES[$RANDOM % ${#NODES[@]}]}

    # TRES allocation
    tres="1=$cpus,2=$mem,4=$nodes,5=$cpus"

    # Random times (within last month)
    submit_offset=$((RANDOM % 2592000))  # Random second in last 30 days
    submit_time=$(date -u -v-${submit_offset}S "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -u -d "@$(($(date +%s) - submit_offset))" "+%Y-%m-%d %H:%M:%S")

    queue_time=$((RANDOM % 600))  # 0-10 minutes queue
    start_time=$(date -u -v+${queue_time}S -d "$submit_time" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -u -d "$submit_time +${queue_time} seconds" "+%Y-%m-%d %H:%M:%S")

    run_time=$((RANDOM % 3600 + 60))  # 1 minute to 1 hour runtime
    end_time=$(date -u -v+${run_time}S -d "$start_time" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || date -u -d "$start_time +${run_time} seconds" "+%Y-%m-%d %H:%M:%S")

    # Write job record
    echo "$user,$group,$account,$cpus,$mem,$nodes,$node,\"$tres\",$submit_time,$start_time,$end_time" >> "$OUTPUT_FILE"

    # Progress indicator
    if [ $((i % 100)) -eq 0 ]; then
        echo "Generated $i jobs..."
    fi
done

echo ""
echo "Sample data generated: $OUTPUT_FILE"
echo "Total jobs: $NUM_JOBS"
echo "Unique users: ${#USERS[@]}"
echo "Unique groups: ${#GROUPS[@]}"
echo ""
echo "Sample (first 5 rows):"
head -n 6 "$OUTPUT_FILE"
echo ""
echo "To anonymize this data, run:"
echo "  ./anonymize_cluster_data.sh $OUTPUT_FILE ${OUTPUT_FILE%.csv}_anon.csv mapping.txt"
