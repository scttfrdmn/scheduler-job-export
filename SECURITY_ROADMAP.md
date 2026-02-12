# Security Roadmap: B+ to A+

## Current Status: B+ (Production Ready)

The codebase already has excellent security practices. To achieve **A+ grade**, we need to address all identified issues and add defense-in-depth measures.

---

## Required for A+ Grade

### 1. Fix All Medium Severity Issues (REQUIRED)

#### 1.1 Add Date Input Validation

**Status**: Validation library created, needs integration

**Implementation**:

```bash
# In export_with_users.sh, add at top:
source "$(dirname "$0")/validation.sh"

# Before using date arguments:
START_DATE="${1:-$(date -d '1 year ago' '+%Y-%m-%d')}"
END_DATE="${2:-$(date '+%Y-%m-%d')}"

if ! validate_date_slurm "$START_DATE"; then
    exit 1
fi

if ! validate_date_slurm "$END_DATE"; then
    exit 1
fi
```

**Apply to**:
- export_with_users.sh (SLURM)
- export_lsf_comprehensive.sh (LSF)
- export_pbs_comprehensive.sh (PBS)
- export_uge_comprehensive.sh (UGE)
- All other export_*.sh scripts

**Effort**: 2-3 hours
**Priority**: HIGH

---

#### 1.2 Add CSV Column Data Validation

**Status**: Not started

**Implementation**:

In `anonymize_cluster_data.sh`, after column detection:

```bash
# After line 150, add validation
validate_csv_columns() {
    local csv_file="$1"
    local user_col="$2"
    local group_col="$3"

    # Check that detected columns contain reasonable data
    local sample_users=$(tail -n +2 "$csv_file" | head -10 | cut -d',' -f"$user_col")

    # Validate user column has alphanumeric data
    if ! echo "$sample_users" | grep -qE '^[a-zA-Z0-9_-]+$'; then
        echo "WARNING: User column contains unexpected characters"
        read -p "Continue anyway? (yes/no): " confirm
        [[ "$confirm" == "yes" ]] || return 1
    fi

    return 0
}

# Call after column detection
validate_csv_columns "$INPUT_CSV" "$USER_COL_NUM" "$GROUP_COL_NUM" || exit 1
```

**Effort**: 1-2 hours
**Priority**: MEDIUM

---

#### 1.3 Validate Array Contents Before Python

**Status**: Not started

**Implementation**:

In `export_pbs_comprehensive.sh` and similar scripts:

```bash
# Before line 375, add:
echo "Validating accounting files..."
for file in "${ACCT_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "ERROR: Invalid accounting file: $file"
        exit 1
    fi
    if [ ! -r "$file" ]; then
        echo "ERROR: Cannot read accounting file: $file"
        exit 1
    fi
done

python3 - "${ACCT_FILES[@]}" "$OUTPUT_FILE"
```

**Effort**: 1 hour
**Priority**: MEDIUM

---

### 2. Fix Low Severity Issues (RECOMMENDED)

#### 2.1 Improve Error Message Sanitization

**Implementation**:

```bash
# Add at top of scripts
VERBOSE="${VERBOSE:-0}"

# Replace verbose error messages:
if [ $VERBOSE -eq 1 ]; then
    echo "Available files:"
    ls -1 "$ACCT_DIR" | head -20
else
    echo "No accounting files found in date range"
    echo "Set VERBOSE=1 for detailed output"
fi
```

**Effort**: 1 hour
**Priority**: LOW

---

#### 2.2 Add Explicit File Permission Checks

**Implementation**:

```bash
# In all export scripts, before writing output:
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
if [ ! -w "$OUTPUT_DIR" ]; then
    echo "ERROR: Cannot write to output directory: $OUTPUT_DIR"
    exit 1
fi

# Check if output file exists and is writable
if [ -f "$OUTPUT_FILE" ] && [ ! -w "$OUTPUT_FILE" ]; then
    echo "ERROR: Cannot overwrite existing file: $OUTPUT_FILE"
    exit 1
fi
```

**Effort**: 1 hour
**Priority**: LOW

---

#### 2.3 Add XML Validation (UGE)

**Status**: Already has try-catch, needs documentation

**Documentation update only** - current implementation is secure.

**Effort**: 15 minutes
**Priority**: LOW

---

### 3. Additional Security Hardening (A+ REQUIREMENTS)

#### 3.1 Add Security Logging

**Create**: `security_logging.sh`

```bash
#!/bin/bash

SECURITY_LOG="${SECURITY_LOG:-/tmp/cluster-export-security.log}"

log_security_event() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local user=$(whoami)
    local script=$(basename "$0")

    echo "[$timestamp] [$user] [$script] [$level] $message" >> "$SECURITY_LOG"
}

log_export_start() {
    log_security_event "INFO" "Export started: $*"
}

log_export_complete() {
    local records="$1"
    log_security_event "INFO" "Export completed: $records records"
}

log_validation_failure() {
    log_security_event "WARN" "Validation failed: $*"
}

log_suspicious_input() {
    log_security_event "ALERT" "Suspicious input detected: $*"
}
```

**Integration**:
```bash
# In export scripts:
source "$(dirname "$0")/security_logging.sh"

log_export_start "$@"

# ... export logic ...

log_export_complete "$RECORD_COUNT"
```

**Effort**: 3-4 hours
**Priority**: HIGH for A+

---

#### 3.2 Add Input Sanitization

**Create**: Enhanced validation in `validation.sh`

```bash
# Add to validation.sh:

sanitize_input() {
    local input="$1"
    # Remove any characters that could be dangerous
    # Keep only: alphanumeric, dash, slash, colon (for dates/times)
    echo "$input" | tr -cd '[:alnum:]/-: '
}

detect_injection_attempt() {
    local input="$1"

    # Check for common injection patterns
    if [[ "$input" =~ \$\(|\`|;|\||&&|\>|\< ]]; then
        log_suspicious_input "Potential injection attempt: $input"
        return 0  # Detected
    fi

    return 1  # Clean
}

# Use in scripts:
START_DATE="${1:-...}"
if detect_injection_attempt "$START_DATE"; then
    echo "ERROR: Invalid input detected"
    exit 1
fi
START_DATE=$(sanitize_input "$START_DATE")
```

**Effort**: 2-3 hours
**Priority**: HIGH for A+

---

#### 3.3 Add Checksums for Output Verification

**Implementation**:

```bash
# At end of export scripts:
generate_checksum() {
    local file="$1"
    local checksum_file="${file}.sha256"

    sha256sum "$file" > "$checksum_file"
    chmod 600 "$checksum_file"

    echo "Checksum: $(cat "$checksum_file")"
    echo "Verify with: sha256sum -c $checksum_file"
}

generate_checksum "$OUTPUT_FILE"
```

**Effort**: 1 hour
**Priority**: MEDIUM for A+

---

#### 3.4 Add Rate Limiting

**Implementation**:

```bash
# Create: rate_limiting.sh

RATE_LIMIT_FILE="/tmp/.cluster_export_rate_limit_$(whoami)"
RATE_LIMIT_SECONDS=60  # Minimum seconds between exports

check_rate_limit() {
    if [ -f "$RATE_LIMIT_FILE" ]; then
        local last_run=$(cat "$RATE_LIMIT_FILE")
        local now=$(date +%s)
        local elapsed=$((now - last_run))

        if [ $elapsed -lt $RATE_LIMIT_SECONDS ]; then
            local wait=$((RATE_LIMIT_SECONDS - elapsed))
            echo "ERROR: Rate limit exceeded. Wait $wait seconds."
            return 1
        fi
    fi

    date +%s > "$RATE_LIMIT_FILE"
    chmod 600 "$RATE_LIMIT_FILE"
    return 0
}

# In export scripts:
source "$(dirname "$0")/rate_limiting.sh"
check_rate_limit || exit 1
```

**Effort**: 1-2 hours
**Priority**: LOW for A+

---

### 4. Security Testing (A+ REQUIREMENT)

#### 4.1 Add Fuzzing Tests

**Create**: `security_tests.sh`

```bash
#!/bin/bash

echo "Running security fuzzing tests..."

# Test 1: Command injection attempts
echo "Test 1: Command injection in date parameters"
./export_with_users.sh "2024-01-01; rm -rf /tmp/test" 2>&1 | grep -q "ERROR" && echo "✓ PASS" || echo "✗ FAIL"

./export_with_users.sh "\$(whoami)" 2>&1 | grep -q "ERROR" && echo "✓ PASS" || echo "✗ FAIL"

./export_with_users.sh "\`cat /etc/passwd\`" 2>&1 | grep -q "ERROR" && echo "✓ PASS" || echo "✗ FAIL"

# Test 2: Path traversal attempts
echo "Test 2: Path traversal"
./anonymize_cluster_data.sh "../../../etc/passwd" out.csv map.txt 2>&1 | grep -q "ERROR" && echo "✓ PASS" || echo "✗ FAIL"

# Test 3: SQL injection (if applicable)
echo "Test 3: SQL-like injection patterns"
./anonymize_cluster_data.sh "test.csv'; DROP TABLE--" out.csv map.txt 2>&1 | grep -q "ERROR" && echo "✓ PASS" || echo "✗ FAIL"

# Test 4: Large input
echo "Test 4: Extremely long input"
LONG_INPUT=$(python3 -c "print('A' * 10000)")
./export_with_users.sh "$LONG_INPUT" 2>&1 | grep -q "ERROR" && echo "✓ PASS" || echo "✗ FAIL"

# Test 5: Special characters
echo "Test 5: Special characters"
./export_with_users.sh "2024-01-01<script>alert(1)</script>" 2>&1 | grep -q "ERROR" && echo "✓ PASS" || echo "✗ FAIL"
```

**Effort**: 3-4 hours
**Priority**: HIGH for A+

---

#### 4.2 Add Permission Tests

**In `test_exports.sh`, add**:

```bash
echo "Test: File permission security"
TEMP_FILE=$(mktemp)
chmod 777 "$TEMP_FILE"
./export_with_users.sh
OUTPUT=$(ls -la slurm_jobs_with_users_*.csv 2>/dev/null | head -1)
if echo "$OUTPUT" | grep -q "rw-------"; then
    pass_test "Output files have secure permissions (600)"
else
    fail_test "Output files have insecure permissions"
fi
```

**Effort**: 1 hour
**Priority**: MEDIUM for A+

---

### 5. Documentation Updates (A+ REQUIREMENT)

#### 5.1 Security Audit Compliance Badge

Add to README:
```markdown
[![Security Audit](https://img.shields.io/badge/Security%20Audit-A+-brightgreen.svg)](SECURITY.md)
```

#### 5.2 Security Quick Start Guide

Add to README after badges:
```markdown
## Security Quick Start

✓ **Safe by default** - All scripts use secure bash practices
✓ **Input validation** - Date parameters and file paths validated
✓ **Audit logging** - Security events logged for review
✓ **Secure permissions** - Sensitive files protected (chmod 600)

See [SECURITY.md](SECURITY.md) for complete security documentation.
```

**Effort**: 30 minutes
**Priority**: HIGH for A+

---

## Implementation Plan

### Phase 1: Critical Fixes (Week 1)
**Required for A+ baseline**

- [ ] Integrate date validation into all export scripts
- [ ] Add security logging framework
- [ ] Add input sanitization
- [ ] Create fuzzing test suite
- [ ] Update documentation

**Estimated effort**: 12-15 hours
**Outcome**: Addresses all medium issues + core A+ requirements

---

### Phase 2: Enhanced Security (Week 2)
**Polish for solid A+**

- [ ] Add CSV column validation
- [ ] Add array content validation
- [ ] Implement checksum generation
- [ ] Add permission tests
- [ ] Improve error sanitization

**Estimated effort**: 8-10 hours
**Outcome**: All known issues resolved

---

### Phase 3: Advanced Features (Week 3)
**Exceptional A+ with extras**

- [ ] Add rate limiting
- [ ] Implement audit trail
- [ ] Add security monitoring dashboard
- [ ] Create incident response playbook
- [ ] Security training documentation

**Estimated effort**: 10-12 hours
**Outcome**: Best-in-class security posture

---

## Quick Win: Immediate A- Grade

If time is limited, focus on Phase 1 only:

```bash
# 1. Integrate validation (3 hours)
for script in export_*.sh; do
    # Add validation.sh sourcing
    # Add date validation calls
done

# 2. Add fuzzing tests (2 hours)
./security_tests.sh

# 3. Update docs (1 hour)
# Add security badges and quick start
```

**Total: 6 hours → Immediate upgrade to A-**
**Full A+: Phases 1+2 → 20-25 hours**

---

## Maintenance for A+

Once A+ is achieved:

1. **Monthly**: Run fuzzing tests
2. **Quarterly**: Security audit review
3. **Per release**: Update SECURITY.md
4. **Annually**: Third-party security assessment

---

## Cost-Benefit Analysis

**Current B+ Status**:
- Secure enough for production use
- All critical vulnerabilities addressed
- Strong foundation

**A+ Benefits**:
- Defense-in-depth protection
- Audit trail for compliance
- Automated security testing
- Industry-leading security posture
- Suitable for high-security environments

**Recommendation**:
- **If administrative use only**: B+ is sufficient
- **If sharing publicly or high-security env**: Invest in A+
- **If compliance required (SOC2, ISO27001)**: A+ recommended

---

## Success Criteria for A+

- ✓ All medium issues resolved
- ✓ 75%+ of low issues addressed
- ✓ Fuzzing test suite passes
- ✓ Security logging implemented
- ✓ Input sanitization in place
- ✓ Audit trail available
- ✓ Documentation complete
- ✓ Automated security tests in CI

**When complete**: Update SECURITY.md with A+ grade and audit date.
