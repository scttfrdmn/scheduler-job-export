#!/bin/bash
#
# Security Logging Framework
#
# Provides logging functions for security events and audit trail.
# Source this file in scripts that need security logging.
#

# Security log location (can be overridden via environment)
SECURITY_LOG="${SECURITY_LOG:-${HOME}/.cluster-export-security.log}"

# Initialize log file with secure permissions
init_security_log() {
    if [ ! -f "$SECURITY_LOG" ]; then
        touch "$SECURITY_LOG"
        chmod 600 "$SECURITY_LOG"
    fi
}

# Core logging function
log_security_event() {
    local level="$1"
    shift
    local message="$*"

    init_security_log

    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local user=$(whoami)
    local script=$(basename "${0}")
    local pid=$$

    # Format: [timestamp] [user] [script:pid] [LEVEL] message
    echo "[$timestamp] [$user] [$script:$pid] [$level] $message" >> "$SECURITY_LOG"
}

# Log export operation start
log_export_start() {
    local scheduler="$1"
    shift
    local args="$*"

    log_security_event "INFO" "Export started: scheduler=$scheduler args='$args'"
}

# Log export completion
log_export_complete() {
    local scheduler="$1"
    local records="$2"
    local output_file="$3"

    log_security_event "INFO" "Export completed: scheduler=$scheduler records=$records output='$output_file'"
}

# Log validation failure
log_validation_failure() {
    local validation_type="$1"
    local input="$2"

    # Sanitize input before logging to prevent log injection
    input=$(echo "$input" | tr -d '\n\r' | cut -c1-100)

    log_security_event "WARN" "Validation failed: type=$validation_type input='$input'"
}

# Log suspicious input detection
log_suspicious_input() {
    local input="$1"
    local reason="$2"

    # Sanitize input before logging
    input=$(echo "$input" | tr -d '\n\r' | cut -c1-100)

    log_security_event "ALERT" "Suspicious input detected: reason='$reason' input='$input'"
}

# Log anonymization operation
log_anonymization() {
    local input_file="$1"
    local output_file="$2"
    local records="$3"

    log_security_event "INFO" "Anonymization: input='$(basename "$input_file")' output='$(basename "$output_file")' records=$records"
}

# Log file access attempt
log_file_access() {
    local operation="$1"
    local file="$2"
    local result="$3"

    log_security_event "INFO" "File access: operation=$operation file='$(basename "$file")' result=$result"
}

# Log permission issue
log_permission_issue() {
    local resource="$1"
    local required_permission="$2"

    log_security_event "ERROR" "Permission denied: resource='$resource' required='$required_permission'"
}

# Log security check result
log_security_check() {
    local check_name="$1"
    local result="$2"
    local details="$3"

    log_security_event "INFO" "Security check: name='$check_name' result=$result details='$details'"
}

# View recent security log entries
show_security_log() {
    local lines="${1:-20}"

    if [ -f "$SECURITY_LOG" ]; then
        echo "Recent security events (last $lines):"
        echo "========================================"
        tail -n "$lines" "$SECURITY_LOG"
    else
        echo "No security log found at: $SECURITY_LOG"
    fi
}

# Search security log for specific events
search_security_log() {
    local pattern="$1"

    if [ -f "$SECURITY_LOG" ]; then
        echo "Security events matching: $pattern"
        echo "========================================"
        grep -i "$pattern" "$SECURITY_LOG"
    else
        echo "No security log found at: $SECURITY_LOG"
    fi
}

# Get security statistics
security_stats() {
    if [ ! -f "$SECURITY_LOG" ]; then
        echo "No security log found"
        return
    fi

    echo "Security Log Statistics"
    echo "========================================"
    echo "Log file: $SECURITY_LOG"
    echo "Total events: $(wc -l < "$SECURITY_LOG")"
    echo ""
    echo "Events by level:"
    grep -oE '\[(INFO|WARN|ERROR|ALERT)\]' "$SECURITY_LOG" | sort | uniq -c | sort -rn
    echo ""
    echo "Recent alerts (last 10):"
    grep '\[ALERT\]' "$SECURITY_LOG" | tail -10
}

# Generate SHA256 checksum for file integrity verification
generate_checksum() {
    local file="$1"
    local checksum_file="${file}.sha256"

    if [ ! -f "$file" ]; then
        log_error "Cannot generate checksum: file not found: $file"
        return 1
    fi

    # Generate checksum
    if command -v sha256sum &> /dev/null; then
        sha256sum "$file" > "$checksum_file"
    elif command -v shasum &> /dev/null; then
        shasum -a 256 "$file" > "$checksum_file"
    else
        log_error "No SHA256 tool available (tried sha256sum, shasum)"
        return 1
    fi

    # Secure the checksum file
    chmod 600 "$checksum_file"

    log_info "Checksum generated: $checksum_file"
    echo ""
    echo "File Integrity Checksum:"
    echo "  File: $(basename "$file")"
    echo "  SHA256: $(cat "$checksum_file")"
    echo "  Checksum file: $checksum_file"
    echo ""
    echo "Verify integrity with:"
    if command -v sha256sum &> /dev/null; then
        echo "  sha256sum -c $checksum_file"
    else
        echo "  shasum -a 256 -c $checksum_file"
    fi

    return 0
}

# Verify file checksum
verify_checksum() {
    local file="$1"
    local checksum_file="${file}.sha256"

    if [ ! -f "$checksum_file" ]; then
        log_error "Checksum file not found: $checksum_file"
        return 1
    fi

    echo "Verifying checksum for: $(basename "$file")"

    if command -v sha256sum &> /dev/null; then
        if sha256sum -c "$checksum_file" 2>&1 | grep -q "OK"; then
            log_info "Checksum verification: PASS for $file"
            echo "✓ Checksum verification: PASS"
            return 0
        else
            log_security_event "ALERT" "Checksum verification FAILED for $file"
            echo "✗ Checksum verification: FAILED"
            return 1
        fi
    elif command -v shasum &> /dev/null; then
        if shasum -a 256 -c "$checksum_file" 2>&1 | grep -q "OK"; then
            log_info "Checksum verification: PASS for $file"
            echo "✓ Checksum verification: PASS"
            return 0
        else
            log_security_event "ALERT" "Checksum verification FAILED for $file"
            echo "✗ Checksum verification: FAILED"
            return 1
        fi
    else
        log_error "No SHA256 tool available for verification"
        return 1
    fi
}

# Export functions for use by other scripts
export -f log_security_event
export -f log_export_start
export -f log_export_complete
export -f log_validation_failure
export -f log_suspicious_input
export -f log_anonymization
export -f log_file_access
export -f log_permission_issue
export -f log_security_check
export -f generate_checksum
export -f verify_checksum
