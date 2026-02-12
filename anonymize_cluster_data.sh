#!/bin/bash
#
# Cluster Job Data Anonymization Script
#
# This script anonymizes user and group information in SLURM job data
# while preserving the ability to analyze per-user and per-group patterns.
#
# Features:
# - Deterministic mapping (same user always gets same anonymous ID)
# - Separate mapping for users and groups
# - Preserves all other job data intact
# - Creates secure mapping file for admin reference
# - Handles large CSV files efficiently
#
# Usage: ./anonymize_cluster_data.sh input.csv output.csv [mapping_file]
#

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
MAPPING_FILE="${3:-mapping_secure.txt}"
TEMP_DIR=$(mktemp -d)

trap 'rm -rf "$TEMP_DIR"' EXIT

# Function to print colored output
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to print usage
usage() {
    cat << EOF
Usage: $0 <input_csv> <output_csv> [mapping_file]

Anonymizes user and group information in cluster job data.

Arguments:
  input_csv      Input CSV file with user/group columns
  output_csv     Output CSV file with anonymized data
  mapping_file   Optional: File to store user/group mappings (default: mapping_secure.txt)

Expected CSV columns (in any order):
  - user, uid, account, or username (user identification)
  - group, gid, or groupname (group identification)
  - hostname, nodename, host, or node (hostname identification)
  - Plus any other job or cluster data columns

The script will:
  1. Identify user, group, and hostname columns automatically
  2. Create consistent anonymous IDs (user_0001, group_A, node_0001, etc.)
  3. Preserve all relationships and other data
  4. Save mapping to secure file (restrict access!)
  5. Output anonymized CSV for sharing

Example:
  $0 jobs_with_users.csv jobs_anonymized.csv mappings.txt

Security Notes:
  - Keep mapping file SECURE and RESTRICTED
  - Mapping file allows de-anonymization
  - Set appropriate permissions: chmod 600 mapping_file
  - Store in secure location with admin-only access

EOF
    exit 1
}

# Check arguments
if [ $# -lt 2 ]; then
    log_error "Missing required arguments"
    usage
fi

INPUT_CSV="$1"
OUTPUT_CSV="$2"

# Validate input file
if [ ! -f "$INPUT_CSV" ]; then
    log_error "Input file not found: $INPUT_CSV"
    exit 1
fi

if [ ! -r "$INPUT_CSV" ]; then
    log_error "Input file not readable: $INPUT_CSV"
    exit 1
fi

log_info "Starting anonymization process..."
log_info "Input file: $INPUT_CSV"
log_info "Output file: $OUTPUT_CSV"
log_info "Mapping file: $MAPPING_FILE"

# Read CSV header
HEADER=$(head -n 1 "$INPUT_CSV")
log_info "Detected columns: $HEADER"

# Detect user, group, and hostname columns
USER_COL=""
GROUP_COL=""
HOSTNAME_COL=""
ACCOUNT_COL=""
COL_NUM=1

IFS=',' read -ra COLS <<< "$HEADER"
for col in "${COLS[@]}"; do
    col_lower=$(echo "$col" | tr '[:upper:]' '[:lower:]' | tr -d ' ')

    # Detect user column (prefer 'user' over 'account')
    if [[ "$col_lower" =~ ^(user|uid|username)$ ]]; then
        USER_COL="$col"
        USER_COL_NUM=$COL_NUM
        log_info "Found user column: '$USER_COL' (position $USER_COL_NUM)"
    elif [[ "$col_lower" =~ ^(account)$ ]] && [ -z "$USER_COL" ]; then
        # Only use 'account' if no 'user' column found yet
        ACCOUNT_COL="$col"
        ACCOUNT_COL_NUM=$COL_NUM
        log_info "Found account column: '$ACCOUNT_COL' (position $ACCOUNT_COL_NUM)"
    fi

    # Detect group column
    if [[ "$col_lower" =~ ^(group|gid|groupname)$ ]]; then
        GROUP_COL="$col"
        GROUP_COL_NUM=$COL_NUM
        log_info "Found group column: '$GROUP_COL' (position $GROUP_COL_NUM)"
    fi

    # Detect hostname column
    if [[ "$col_lower" =~ ^(hostname|nodename|nodelist|host|node)$ ]]; then
        HOSTNAME_COL="$col"
        HOSTNAME_COL_NUM=$COL_NUM
        log_info "Found hostname column: '$HOSTNAME_COL' (position $HOSTNAME_COL_NUM)"
    fi

    ((COL_NUM++))
done

# If no explicit 'user' column found, use 'account' as fallback
if [ -z "$USER_COL" ] && [ -n "$ACCOUNT_COL" ]; then
    USER_COL="$ACCOUNT_COL"
    USER_COL_NUM=$ACCOUNT_COL_NUM
    log_info "Using account column as user column (no explicit 'user' column found)"
fi

# Validate columns found
if [ -z "$USER_COL" ] && [ -z "$GROUP_COL" ] && [ -z "$HOSTNAME_COL" ]; then
    log_error "No user, group, or hostname columns detected in CSV"
    log_error "Expected columns like: user, uid, username, account, group, gid, groupname, hostname, nodename"
    log_error "Found: $HEADER"
    exit 1
fi

# Validate column data content (security check)
log_info "Validating column data integrity..."

validate_column_data() {
    local col_num="$1"
    local col_name="$2"
    local col_type="$3"  # user, group, or hostname

    # Sample first 10 data rows (skip header)
    local sample=$(tail -n +2 "$INPUT_CSV" | head -10 | cut -d',' -f"$col_num" | tr -d '"')

    # Count non-empty values
    local non_empty=$(echo "$sample" | grep -v '^$' | wc -l | tr -d ' ')

    if [ "$non_empty" -eq 0 ]; then
        log_warn "Column '$col_name' appears to be empty in sample data"
        return 1
    fi

    # Validate data patterns based on type
    case "$col_type" in
        user)
            # Users should be alphanumeric with optional dash, underscore, dot
            if echo "$sample" | grep -qE '^[a-zA-Z0-9._-]+$'; then
                log_info "✓ User column '$col_name' data looks valid"
                return 0
            else
                log_warn "⚠ User column '$col_name' contains unexpected characters"
                log_warn "Sample values:"
                echo "$sample" | head -3 | sed 's/^/    /' >&2
                return 1
            fi
            ;;
        group)
            # Groups similar to users
            if echo "$sample" | grep -qE '^[a-zA-Z0-9._-]+$'; then
                log_info "✓ Group column '$col_name' data looks valid"
                return 0
            else
                log_warn "⚠ Group column '$col_name' contains unexpected characters"
                return 1
            fi
            ;;
        hostname)
            # Hostnames can have dots, dashes, alphanumeric, and commas (for nodelists)
            if echo "$sample" | grep -qE '^[a-zA-Z0-9.,:_-]+$'; then
                log_info "✓ Hostname column '$col_name' data looks valid"
                return 0
            else
                log_warn "⚠ Hostname column '$col_name' contains unexpected characters"
                return 1
            fi
            ;;
    esac
}

# Validate detected columns
VALIDATION_WARNINGS=0

if [ -n "$USER_COL" ]; then
    if ! validate_column_data "$USER_COL_NUM" "$USER_COL" "user"; then
        VALIDATION_WARNINGS=$((VALIDATION_WARNINGS + 1))
    fi
fi

if [ -n "$GROUP_COL" ]; then
    if ! validate_column_data "$GROUP_COL_NUM" "$GROUP_COL" "group"; then
        VALIDATION_WARNINGS=$((VALIDATION_WARNINGS + 1))
    fi
fi

if [ -n "$HOSTNAME_COL" ]; then
    if ! validate_column_data "$HOSTNAME_COL_NUM" "$HOSTNAME_COL" "hostname"; then
        VALIDATION_WARNINGS=$((VALIDATION_WARNINGS + 1))
    fi
fi

# Ask user to confirm if warnings found
if [ $VALIDATION_WARNINGS -gt 0 ]; then
    log_warn "Found $VALIDATION_WARNINGS validation warnings"
    echo ""
    read -p "Continue with anonymization anyway? (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_error "Anonymization cancelled by user due to validation warnings"
        exit 1
    fi
    log_info "User confirmed to continue despite warnings"
fi

# Extract unique users, groups, and hostnames
log_info "Extracting unique users, groups, and hostnames..."

if [ -n "$USER_COL" ]; then
    tail -n +2 "$INPUT_CSV" | cut -d',' -f"$USER_COL_NUM" | sort -u > "$TEMP_DIR/users.txt"
    NUM_USERS=$(wc -l < "$TEMP_DIR/users.txt")
    log_info "Found $NUM_USERS unique users"
fi

if [ -n "$GROUP_COL" ]; then
    tail -n +2 "$INPUT_CSV" | cut -d',' -f"$GROUP_COL_NUM" | sort -u > "$TEMP_DIR/groups.txt"
    NUM_GROUPS=$(wc -l < "$TEMP_DIR/groups.txt")
    log_info "Found $NUM_GROUPS unique groups"
fi

if [ -n "$HOSTNAME_COL" ]; then
    tail -n +2 "$INPUT_CSV" | cut -d',' -f"$HOSTNAME_COL_NUM" | sort -u > "$TEMP_DIR/hostnames.txt"
    NUM_HOSTNAMES=$(wc -l < "$TEMP_DIR/hostnames.txt")
    log_info "Found $NUM_HOSTNAMES unique hostnames"
fi

# Generate mapping files
log_info "Generating anonymous mappings..."

# User mapping
if [ -n "$USER_COL" ]; then
    counter=1
    while IFS= read -r user; do
        # Skip empty lines
        [ -z "$user" ] && continue

        # Generate anonymous ID with zero-padding
        anon_id=$(printf "user_%04d" $counter)
        echo "$user -> $anon_id"

        # Store mapping
        echo "USER: $user -> $anon_id" >> "$TEMP_DIR/mapping.txt"

        # Store for sed replacement
        echo "s|^\\([^,]*,\\)\\{$((USER_COL_NUM-1))\\}\\K$user|$anon_id|g" >> "$TEMP_DIR/sed_users.txt"

        ((counter++))
    done < "$TEMP_DIR/users.txt"
    log_info "Created $((counter-1)) user mappings"
fi

# Group mapping (using letters)
if [ -n "$GROUP_COL" ]; then
    counter=1
    while IFS= read -r group; do
        # Skip empty lines
        [ -z "$group" ] && continue

        # Generate anonymous ID (group_A, group_B, etc.)
        # For >26 groups, use group_AA, group_AB, etc.
        if [ $counter -le 26 ]; then
            letter=$(printf "\\$(printf '%03o' $((64+counter)))")
            anon_id="group_${letter}"
        else
            idx=$((counter-27))
            first=$((idx/26 + 65))
            second=$((idx%26 + 65))
            anon_id="group_$(printf "\\$(printf '%03o' $first)")$(printf "\\$(printf '%03o' $second)")"
        fi

        echo "$group -> $anon_id"

        # Store mapping
        echo "GROUP: $group -> $anon_id" >> "$TEMP_DIR/mapping.txt"

        ((counter++))
    done < "$TEMP_DIR/groups.txt"
    log_info "Created $((counter-1)) group mappings"
fi

# Create a more robust Python script for anonymization
log_info "Creating anonymization processor..."

cat > "$TEMP_DIR/anonymize.py" << 'PYTHON_EOF'
#!/usr/bin/env python3
import sys
import csv
import hashlib
import os

def anonymize_csv(input_file, output_file, mapping_file, user_col_idx, group_col_idx, hostname_col_idx):
    """Anonymize CSV data with consistent mappings"""

    user_map = {}
    group_map = {}
    hostname_map = {}
    user_counter = 1
    group_counter = 1
    hostname_counter = 1

    # Read and anonymize
    with open(input_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        # Write header
        header = next(reader)
        writer.writerow(header)

        # Process rows
        for row in reader:
            # Anonymize user
            if user_col_idx is not None and user_col_idx < len(row):
                user = row[user_col_idx]
                if user and user not in user_map:
                    user_map[user] = f"user_{user_counter:04d}"
                    user_counter += 1
                if user:
                    row[user_col_idx] = user_map[user]

            # Anonymize group
            if group_col_idx is not None and group_col_idx < len(row):
                group = row[group_col_idx]
                if group and group not in group_map:
                    # Generate group letter(s)
                    if group_counter <= 26:
                        letter = chr(64 + group_counter)
                    else:
                        idx = group_counter - 27
                        first = chr(idx // 26 + 65)
                        second = chr(idx % 26 + 65)
                        letter = first + second
                    group_map[group] = f"group_{letter}"
                    group_counter += 1
                if group:
                    row[group_col_idx] = group_map[group]

            # Anonymize hostname
            if hostname_col_idx is not None and hostname_col_idx < len(row):
                hostname = row[hostname_col_idx]
                if hostname and hostname not in hostname_map:
                    hostname_map[hostname] = f"node_{hostname_counter:04d}"
                    hostname_counter += 1
                if hostname:
                    row[hostname_col_idx] = hostname_map[hostname]

            writer.writerow(row)

    # Write mapping file
    with open(mapping_file, 'w') as mapfile:
        mapfile.write("=" * 80 + "\n")
        mapfile.write("CLUSTER DATA ANONYMIZATION MAPPING\n")
        mapfile.write("=" * 80 + "\n")
        mapfile.write("CONFIDENTIAL - ADMIN ACCESS ONLY\n")
        mapfile.write("=" * 80 + "\n\n")

        if user_map:
            mapfile.write("USER MAPPINGS:\n")
            mapfile.write("-" * 80 + "\n")
            for real, anon in sorted(user_map.items(), key=lambda x: x[1]):
                mapfile.write(f"{anon:15s} -> {real}\n")
            mapfile.write("\n")

        if group_map:
            mapfile.write("GROUP MAPPINGS:\n")
            mapfile.write("-" * 80 + "\n")
            for real, anon in sorted(group_map.items(), key=lambda x: x[1]):
                mapfile.write(f"{anon:15s} -> {real}\n")
            mapfile.write("\n")

        if hostname_map:
            mapfile.write("HOSTNAME MAPPINGS:\n")
            mapfile.write("-" * 80 + "\n")
            for real, anon in sorted(hostname_map.items(), key=lambda x: x[1]):
                mapfile.write(f"{anon:15s} -> {real}\n")
            mapfile.write("\n")

        mapfile.write("=" * 80 + "\n")
        mapfile.write(f"Total users anonymized: {len(user_map)}\n")
        mapfile.write(f"Total groups anonymized: {len(group_map)}\n")
        mapfile.write(f"Total hostnames anonymized: {len(hostname_map)}\n")
        mapfile.write("=" * 80 + "\n")

    return len(user_map), len(group_map), len(hostname_map)

if __name__ == "__main__":
    input_csv = sys.argv[1]
    output_csv = sys.argv[2]
    mapping_file = sys.argv[3]
    user_col = int(sys.argv[4]) if sys.argv[4] != "None" else None
    group_col = int(sys.argv[5]) if sys.argv[5] != "None" else None
    hostname_col = int(sys.argv[6]) if sys.argv[6] != "None" else None

    if user_col is not None:
        user_col -= 1  # Convert to 0-indexed
    if group_col is not None:
        group_col -= 1  # Convert to 0-indexed
    if hostname_col is not None:
        hostname_col -= 1  # Convert to 0-indexed

    users, groups, hostnames = anonymize_csv(input_csv, output_csv, mapping_file, user_col, group_col, hostname_col)
    print(f"Anonymized {users} users, {groups} groups, and {hostnames} hostnames")

PYTHON_EOF

chmod +x "$TEMP_DIR/anonymize.py"

# Run anonymization
log_info "Processing CSV file..."

USER_ARG="${USER_COL_NUM:-None}"
GROUP_ARG="${GROUP_COL_NUM:-None}"
HOSTNAME_ARG="${HOSTNAME_COL_NUM:-None}"

python3 "$TEMP_DIR/anonymize.py" "$INPUT_CSV" "$OUTPUT_CSV" "$MAPPING_FILE" "$USER_ARG" "$GROUP_ARG" "$HOSTNAME_ARG"

# Set secure permissions on mapping file
chmod 600 "$MAPPING_FILE"
log_info "Mapping file created with restricted permissions (600)"

# Print summary
log_info "Anonymization complete!"
echo ""
log_info "Summary:"
log_info "  Input rows: $(tail -n +2 "$INPUT_CSV" | wc -l)"
log_info "  Output rows: $(tail -n +2 "$OUTPUT_CSV" | wc -l)"
log_info "  Output file: $OUTPUT_CSV"
log_info "  Mapping file: $MAPPING_FILE"

echo ""
log_warn "SECURITY REMINDER:"
log_warn "  1. The mapping file ($MAPPING_FILE) allows de-anonymization"
log_warn "  2. Restrict access to admin-only: chmod 600 $MAPPING_FILE"
log_warn "  3. Store in secure location with limited access"
log_warn "  4. Consider encrypting: gpg -c $MAPPING_FILE"
log_warn "  5. Do NOT share mapping file with anonymized data"

echo ""
log_info "The anonymized CSV can now be safely shared for analysis."
log_info "Users and groups are consistently mapped, preserving patterns."

# Show sample
echo ""
log_info "Sample of anonymized data (first 5 rows):"
head -n 6 "$OUTPUT_CSV"

exit 0
