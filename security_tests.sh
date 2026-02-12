#!/bin/bash
#
# Security Fuzzing Test Suite
#
# Tests export scripts against malicious inputs to validate security controls.
#

set -euo pipefail

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================================================"
echo "Security Fuzzing Test Suite"
echo "================================================================"
echo ""

# Test result function
test_result() {
    local test_name="$1"
    local command="$2"
    local expected_exit="$3"  # 0=should succeed, 1=should fail

    TESTS_TOTAL=$((TESTS_TOTAL + 1))

    # Run the command and capture exit code
    set +e
    eval "$command" >/dev/null 2>&1
    local exit_code=$?
    set -e

    if [ "$expected_exit" -eq 0 ]; then
        # Should succeed
        if [ $exit_code -eq 0 ]; then
            echo -e "${GREEN}✓ PASS${NC}: $test_name"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}✗ FAIL${NC}: $test_name (expected success, got exit $exit_code)"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        # Should fail
        if [ $exit_code -ne 0 ]; then
            echo -e "${GREEN}✓ PASS${NC}: $test_name (correctly rejected)"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}✗ FAIL${NC}: $test_name (should have rejected input)"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    fi
}

echo -e "${BLUE}Category 1: Command Injection Tests${NC}"
echo "Testing for shell command injection vulnerabilities..."
echo ""

# Test 1.1: Command substitution with $()
test_result "Command injection - \$(whoami)" \
    "./export_with_users.sh '2024-01-01; \$(whoami)' 2024-12-31" \
    1

# Test 1.2: Command substitution with backticks
test_result "Command injection - backticks" \
    "./export_with_users.sh '\`cat /etc/passwd\`' 2024-12-31" \
    1

# Test 1.3: Semicolon command chaining
test_result "Command injection - semicolon" \
    "./export_with_users.sh '2024-01-01; rm -rf /tmp/test' 2024-12-31" \
    1

# Test 1.4: Pipe command
test_result "Command injection - pipe" \
    "./export_with_users.sh '2024-01-01 | cat /etc/passwd' 2024-12-31" \
    1

# Test 1.5: AND operator
test_result "Command injection - AND" \
    "./export_with_users.sh '2024-01-01 && whoami' 2024-12-31" \
    1

# Test 1.6: OR operator
test_result "Command injection - OR" \
    "./export_with_users.sh '2024-01-01 || whoami' 2024-12-31" \
    1

# Test 1.7: Redirection
test_result "Command injection - redirection" \
    "./export_with_users.sh '2024-01-01 > /tmp/evil' 2024-12-31" \
    1

echo ""
echo -e "${BLUE}Category 2: Path Traversal Tests${NC}"
echo "Testing for directory traversal vulnerabilities..."
echo ""

# Create test CSV for anonymization tests
TEST_CSV=$(mktemp)
echo "user,group,job_id" > "$TEST_CSV"
echo "testuser,testgroup,12345" >> "$TEST_CSV"
trap 'rm -f "$TEST_CSV"' EXIT

# Test 2.1: Parent directory traversal
test_result "Path traversal - parent directory" \
    "./anonymize_cluster_data.sh '../../../etc/passwd' /tmp/out.csv /tmp/map.txt" \
    1

# Test 2.2: Absolute path to sensitive file
test_result "Path traversal - /etc/passwd" \
    "./anonymize_cluster_data.sh '/etc/passwd' /tmp/out.csv /tmp/map.txt" \
    1

# Test 2.3: Null byte injection
test_result "Path traversal - null byte" \
    "./anonymize_cluster_data.sh 'test.csv\x00/etc/passwd' /tmp/out.csv /tmp/map.txt" \
    1

echo ""
echo -e "${BLUE}Category 3: Input Length Tests${NC}"
echo "Testing handling of extremely long inputs..."
echo ""

# Test 3.1: Very long date string
LONG_DATE=$(python3 -c "print('2024-01-01' + 'A' * 10000)")
test_result "Long input - 10KB date string" \
    "./export_with_users.sh '$LONG_DATE' 2024-12-31" \
    1

# Test 3.2: Very long filename
LONG_FILENAME=$(python3 -c "print('A' * 5000 + '.csv')")
test_result "Long input - 5KB filename" \
    "./anonymize_cluster_data.sh '$TEST_CSV' '$LONG_FILENAME' /tmp/map.txt" \
    1

echo ""
echo -e "${BLUE}Category 4: Special Characters Tests${NC}"
echo "Testing handling of special characters..."
echo ""

# Test 4.1: HTML/XSS-like input
test_result "Special chars - HTML tags" \
    "./export_with_users.sh '2024-01-01<script>alert(1)</script>' 2024-12-31" \
    1

# Test 4.2: SQL-like injection
test_result "Special chars - SQL injection" \
    "./export_with_users.sh \"2024-01-01' OR '1'='1\" 2024-12-31" \
    1

# Test 4.3: Format string
test_result "Special chars - format string" \
    "./export_with_users.sh '2024-01-01%s%s%s%s' 2024-12-31" \
    1

# Test 4.4: Control characters
test_result "Special chars - newline" \
    "./export_with_users.sh $'2024-01-01\n/etc/passwd' 2024-12-31" \
    1

# Test 4.5: Unicode/UTF-8
test_result "Special chars - unicode" \
    "./export_with_users.sh '2024-01-01™©®' 2024-12-31" \
    1

echo ""
echo -e "${BLUE}Category 5: Valid Input Tests${NC}"
echo "Testing that valid inputs are accepted..."
echo ""

# Test 5.1: Normal SLURM date
test_result "Valid input - SLURM date" \
    "./export_with_users.sh 2024-01-01 2024-01-02" \
    0

# Test 5.2: Valid LSF date (if LSF available)
if command -v bhist &> /dev/null; then
    test_result "Valid input - LSF date" \
        "./export_lsf_comprehensive.sh 2024/01/01 2024/01/02" \
        0
fi

# Test 5.3: Valid PBS date (if PBS available)
if command -v qstat &> /dev/null && [ -d "/var/spool/pbs/server_priv/accounting" ]; then
    test_result "Valid input - PBS date" \
        "sudo ./export_pbs_comprehensive.sh 20240101 20240102" \
        0
fi

# Test 5.4: Valid UGE date (if UGE available)
if command -v qacct &> /dev/null; then
    test_result "Valid input - UGE date" \
        "./export_uge_comprehensive.sh 01/01/2024 01/02/2024" \
        0
fi

# Test 5.5: Valid anonymization
test_result "Valid input - anonymization" \
    "./anonymize_cluster_data.sh '$TEST_CSV' /tmp/test_out.csv /tmp/test_map.txt" \
    0

# Cleanup
rm -f /tmp/test_out.csv /tmp/test_map.txt /tmp/out.csv /tmp/map.txt

echo ""
echo "================================================================"
echo "SECURITY TEST RESULTS"
echo "================================================================"
echo ""
echo "Total tests: $TESTS_TOTAL"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL SECURITY TESTS PASSED${NC}"
    echo ""
    echo "All injection attempts were correctly blocked."
    echo "Valid inputs were correctly accepted."
    exit 0
else
    echo -e "${RED}✗ SOME SECURITY TESTS FAILED${NC}"
    echo ""
    echo "CRITICAL: Some malicious inputs were not properly validated!"
    echo "Review the failed tests above and fix the security issues."
    exit 1
fi
