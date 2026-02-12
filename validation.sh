#!/bin/bash
#
# Input Validation Functions
#
# Security-focused validation functions for scheduler export scripts.
# Source this file in scripts that need input validation.
#

# Validate SLURM date format: YYYY-MM-DD
validate_date_slurm() {
    local date="$1"
    if [[ ! "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo "ERROR: Invalid SLURM date format. Expected: YYYY-MM-DD (e.g., 2024-01-31)" >&2
        return 1
    fi

    # Additional validation: check ranges
    local year month day
    year=$(echo "$date" | cut -d- -f1)
    month=$(echo "$date" | cut -d- -f2)
    day=$(echo "$date" | cut -d- -f3)

    if [ "$year" -lt 2000 ] || [ "$year" -gt 2099 ]; then
        echo "ERROR: Year out of range (2000-2099): $year" >&2
        return 1
    fi

    if [ "$month" -lt 1 ] || [ "$month" -gt 12 ]; then
        echo "ERROR: Month out of range (01-12): $month" >&2
        return 1
    fi

    if [ "$day" -lt 1 ] || [ "$day" -gt 31 ]; then
        echo "ERROR: Day out of range (01-31): $day" >&2
        return 1
    fi

    return 0
}

# Validate LSF date format: YYYY/MM/DD
validate_date_lsf() {
    local date="$1"
    if [[ ! "$date" =~ ^[0-9]{4}/[0-9]{2}/[0-9]{2}$ ]]; then
        echo "ERROR: Invalid LSF date format. Expected: YYYY/MM/DD (e.g., 2024/01/31)" >&2
        return 1
    fi

    local year month day
    year=$(echo "$date" | cut -d/ -f1)
    month=$(echo "$date" | cut -d/ -f2)
    day=$(echo "$date" | cut -d/ -f3)

    if [ "$year" -lt 2000 ] || [ "$year" -gt 2099 ]; then
        echo "ERROR: Year out of range (2000-2099): $year" >&2
        return 1
    fi

    if [ "$month" -lt 1 ] || [ "$month" -gt 12 ]; then
        echo "ERROR: Month out of range (01-12): $month" >&2
        return 1
    fi

    if [ "$day" -lt 1 ] || [ "$day" -gt 31 ]; then
        echo "ERROR: Day out of range (01-31): $day" >&2
        return 1
    fi

    return 0
}

# Validate PBS date format: YYYYMMDD
validate_date_pbs() {
    local date="$1"
    if [[ ! "$date" =~ ^[0-9]{8}$ ]]; then
        echo "ERROR: Invalid PBS date format. Expected: YYYYMMDD (e.g., 20240131)" >&2
        return 1
    fi

    local year month day
    year="${date:0:4}"
    month="${date:4:2}"
    day="${date:6:2}"

    if [ "$year" -lt 2000 ] || [ "$year" -gt 2099 ]; then
        echo "ERROR: Year out of range (2000-2099): $year" >&2
        return 1
    fi

    if [ "$month" -lt 1 ] || [ "$month" -gt 12 ]; then
        echo "ERROR: Month out of range (01-12): $month" >&2
        return 1
    fi

    if [ "$day" -lt 1 ] || [ "$day" -gt 31 ]; then
        echo "ERROR: Day out of range (01-31): $day" >&2
        return 1
    fi

    return 0
}

# Validate UGE date format: MM/DD/YYYY
validate_date_uge() {
    local date="$1"
    if [[ ! "$date" =~ ^[0-9]{2}/[0-9]{2}/[0-9]{4}$ ]]; then
        echo "ERROR: Invalid UGE date format. Expected: MM/DD/YYYY (e.g., 01/31/2024)" >&2
        return 1
    fi

    local month day year
    month=$(echo "$date" | cut -d/ -f1)
    day=$(echo "$date" | cut -d/ -f2)
    year=$(echo "$date" | cut -d/ -f3)

    if [ "$year" -lt 2000 ] || [ "$year" -gt 2099 ]; then
        echo "ERROR: Year out of range (2000-2099): $year" >&2
        return 1
    fi

    if [ "$month" -lt 1 ] || [ "$month" -gt 12 ]; then
        echo "ERROR: Month out of range (01-12): $month" >&2
        return 1
    fi

    if [ "$day" -lt 1 ] || [ "$day" -gt 31 ]; then
        echo "ERROR: Day out of range (01-31): $day" >&2
        return 1
    fi

    return 0
}

# Validate file path (no directory traversal)
validate_file_path() {
    local path="$1"

    # Check for directory traversal patterns
    if [[ "$path" =~ \.\./|/\.\.$ ]]; then
        echo "ERROR: Path contains directory traversal: $path" >&2
        return 1
    fi

    # Check for absolute paths outside allowed directories (optional)
    # Uncomment if you want to restrict to certain directories
    # if [[ "$path" =~ ^/ ]] && [[ ! "$path" =~ ^/home/|^/tmp/ ]]; then
    #     echo "ERROR: Absolute path not in allowed directory: $path" >&2
    #     return 1
    # fi

    return 0
}

# Validate output filename (no special characters that could cause issues)
validate_output_filename() {
    local filename="$1"

    # Allow alphanumeric, underscore, dash, dot, slash (for paths)
    if [[ ! "$filename" =~ ^[a-zA-Z0-9_./+-]+$ ]]; then
        echo "ERROR: Invalid characters in filename: $filename" >&2
        echo "Allowed: letters, numbers, underscore, dash, dot, slash" >&2
        return 1
    fi

    return 0
}

# Test if file exists and is readable
validate_readable_file() {
    local file="$1"

    if [ ! -f "$file" ]; then
        echo "ERROR: File does not exist: $file" >&2
        return 1
    fi

    if [ ! -r "$file" ]; then
        echo "ERROR: File is not readable: $file" >&2
        return 1
    fi

    return 0
}

# Test if directory exists and is writable
validate_writable_directory() {
    local dir="$1"

    if [ ! -d "$dir" ]; then
        echo "ERROR: Directory does not exist: $dir" >&2
        return 1
    fi

    if [ ! -w "$dir" ]; then
        echo "ERROR: Directory is not writable: $dir" >&2
        return 1
    fi

    return 0
}

# Sanitize filename for safe output
sanitize_filename() {
    local filename="$1"
    # Replace any non-alphanumeric (except _ - .) with underscore
    echo "$filename" | tr -c '[:alnum:]_.-' '_'
}
