#!/bin/bash
#
# Test Harness for Scheduler Export Scripts
#
# Tests Python code extraction and basic functionality
#

set -euo pipefail

echo "================================================================"
echo "Test Harness - Scheduler Data Export"
echo "================================================================"
echo ""

TESTS_PASSED=0
TESTS_FAILED=0
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test result functions
pass_test() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail_test() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
}

skip_test() {
    echo -e "${YELLOW}⊘ SKIP${NC}: $1"
}

echo "Running tests..."
echo ""

# Test 1: Check Python 3 is available
echo "Test 1: Python 3 availability"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    pass_test "Python 3 found (version $PYTHON_VERSION)"
else
    fail_test "Python 3 not found"
fi
echo ""

# Test 2: Check bash is recent enough
echo "Test 2: Bash version"
BASH_VERSION_NUM=$(bash --version | head -1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
BASH_MAJOR=$(echo "$BASH_VERSION_NUM" | cut -d. -f1)
if [ "$BASH_MAJOR" -ge 3 ]; then
    pass_test "Bash version acceptable ($BASH_VERSION_NUM)"
else
    fail_test "Bash version too old ($BASH_VERSION_NUM < 3.0)"
fi
echo ""

# Test 3: Check all export scripts are executable
echo "Test 3: Export scripts are executable"
SCRIPTS_OK=0
SCRIPTS_BAD=0
for script in export_*.sh anonymize_cluster_data.sh; do
    if [ ! -f "$script" ]; then
        continue
    fi

    if [ -x "$script" ]; then
        SCRIPTS_OK=$((SCRIPTS_OK + 1))
    else
        echo "  → $script is not executable"
        SCRIPTS_BAD=$((SCRIPTS_BAD + 1))
    fi
done

if [ $SCRIPTS_BAD -eq 0 ]; then
    pass_test "All $SCRIPTS_OK export scripts are executable"
else
    fail_test "$SCRIPTS_BAD scripts are not executable (run: chmod +x *.sh)"
fi
echo ""

# Test 4: Check Python syntax in embedded code
echo "Test 4: Python syntax validation"
SYNTAX_ERRORS=0

for script in export_*.sh anonymize_cluster_data.sh; do
    if [ ! -f "$script" ]; then
        continue
    fi

    # Extract Python code
    in_python=0
    python_code=""
    block_num=0

    while IFS= read -r line; do
        if [[ "$line" =~ python3[[:space:]]*\<\<[[:space:]]*[\'\"]*PYTHON_EOF[\'\"]*[[:space:]]*$ ]]; then
            in_python=1
            python_code=""
            continue
        fi

        if [[ "$line" =~ ^PYTHON_EOF[[:space:]]*$ ]] && [ $in_python -eq 1 ]; then
            in_python=0
            block_num=$((block_num + 1))

            # Test syntax by writing to temp file
            TEST_FILE="$TEMP_DIR/syntax_test_${block_num}.py"
            echo "$python_code" > "$TEST_FILE"

            if ! python3 -m py_compile "$TEST_FILE" 2>/dev/null; then
                echo "  → Syntax error in $script (block $block_num)"
                SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
            fi

            python_code=""
            continue
        fi

        if [ $in_python -eq 1 ]; then
            python_code="${python_code}${line}"$'\n'
        fi
    done < "$script"
done

if [ $SYNTAX_ERRORS -eq 0 ]; then
    pass_test "No Python syntax errors found"
else
    fail_test "Found $SYNTAX_ERRORS Python syntax errors"
fi
echo ""

# Test 5: Check for required standard library imports
echo "Test 5: Standard library import check"
MISSING_IMPORTS=0

for module in csv sys datetime re os collections gzip bz2; do
    if ! python3 -c "import $module" 2>/dev/null; then
        echo "  → Missing module: $module"
        MISSING_IMPORTS=$((MISSING_IMPORTS + 1))
    fi
done

if [ $MISSING_IMPORTS -eq 0 ]; then
    pass_test "All required standard library modules available"
else
    fail_test "Missing $MISSING_IMPORTS required modules"
fi
echo ""

# Test 6: Test anonymization script with sample data
echo "Test 6: Anonymization script functionality"

# Create sample input CSV
cat > "$TEMP_DIR/test_input.csv" << 'EOF'
user,group,account,job_id,nodelist,cpus
alice,research,proj_a,12345,node001.example.com,16
bob,physics,proj_b,12346,node002.example.com,32
alice,research,proj_a,12347,node001.example.com,16
EOF

# Test if anonymize script exists and can run
if [ -f "anonymize_cluster_data.sh" ] && [ -x "anonymize_cluster_data.sh" ]; then
    if ./anonymize_cluster_data.sh \
        "$TEMP_DIR/test_input.csv" \
        "$TEMP_DIR/test_output.csv" \
        "$TEMP_DIR/test_mapping.txt" \
        &> "$TEMP_DIR/anon_test.log"; then

        # Verify output was created
        if [ -f "$TEMP_DIR/test_output.csv" ]; then
            # Check that users were anonymized
            if grep -q "user_0001" "$TEMP_DIR/test_output.csv" && \
               ! grep -q "alice" "$TEMP_DIR/test_output.csv"; then
                pass_test "Anonymization script works correctly"
            else
                fail_test "Anonymization did not transform usernames"
            fi
        else
            fail_test "Anonymization script did not create output file"
        fi
    else
        fail_test "Anonymization script execution failed"
    fi
else
    skip_test "Anonymization script not found or not executable"
fi
echo ""

# Test 7: Check README documentation exists
echo "Test 7: Documentation check"
if [ -f "README.md" ]; then
    # Check for key sections
    MISSING_SECTIONS=""

    if ! grep -q "Quick Start" README.md; then
        MISSING_SECTIONS="${MISSING_SECTIONS}Quick Start, "
    fi
    if ! grep -q "Requirements" README.md; then
        MISSING_SECTIONS="${MISSING_SECTIONS}Requirements, "
    fi
    if ! grep -q "What Gets Exported" README.md; then
        MISSING_SECTIONS="${MISSING_SECTIONS}What Gets Exported, "
    fi

    if [ -z "$MISSING_SECTIONS" ]; then
        pass_test "README documentation is complete"
    else
        fail_test "README missing sections: $MISSING_SECTIONS"
    fi
else
    fail_test "README.md not found"
fi
echo ""

# Test 8: Check for common bash issues (shellcheck if available)
echo "Test 8: Shell script quality (shellcheck)"
if command -v shellcheck &> /dev/null; then
    SHELLCHECK_ERRORS=0

    for script in export_*.sh anonymize_cluster_data.sh lint_python.sh test_exports.sh; do
        if [ ! -f "$script" ]; then
            continue
        fi

        # Run shellcheck (ignore some warnings for heredocs)
        if ! shellcheck -e SC2086 -e SC2181 "$script" &> /dev/null; then
            SHELLCHECK_ERRORS=$((SHELLCHECK_ERRORS + 1))
        fi
    done

    if [ $SHELLCHECK_ERRORS -eq 0 ]; then
        pass_test "All shell scripts pass shellcheck"
    else
        fail_test "$SHELLCHECK_ERRORS scripts have shellcheck warnings"
    fi
else
    skip_test "shellcheck not installed (optional but recommended)"
fi
echo ""

# Test 9: File permission security
echo "Test 9: File permission security"

# Test that security-sensitive files would have secure permissions
PERMISSION_ISSUES=0

# Check security_logging.sh creates secure log file
source security_logging.sh
init_security_log

if [ -f "$SECURITY_LOG" ]; then
    # Get file permissions (portable way)
    if ls -l "$SECURITY_LOG" | grep -q '^-rw-------'; then
        : # Permissions are correct (600)
    elif ls -l "$SECURITY_LOG" | grep -q '^-rw-r--r--'; then
        echo "  → Security log has weak permissions (644 instead of 600)"
        PERMISSION_ISSUES=$((PERMISSION_ISSUES + 1))
    else
        echo "  → Security log has unexpected permissions"
        PERMISSION_ISSUES=$((PERMISSION_ISSUES + 1))
    fi
fi

# Test anonymization creates secure mapping file
TEST_MAP="$TEMP_DIR/test_mapping.txt"
if ./anonymize_cluster_data.sh "$TEMP_DIR/test_input.csv" "$TEMP_DIR/test_anon_output.csv" "$TEST_MAP" &> /dev/null; then
    if [ -f "$TEST_MAP" ]; then
        if ls -l "$TEST_MAP" | grep -q '^-rw-------'; then
            : # Permissions are correct (600)
        else
            echo "  → Mapping file has weak permissions (should be 600)"
            PERMISSION_ISSUES=$((PERMISSION_ISSUES + 1))
        fi
    fi
fi

# Test that checksum files are created with secure permissions
TEST_FILE="$TEMP_DIR/test_checksum.csv"
echo "test,data" > "$TEST_FILE"
if generate_checksum "$TEST_FILE" &> /dev/null; then
    if [ -f "${TEST_FILE}.sha256" ]; then
        if ls -l "${TEST_FILE}.sha256" | grep -q '^-rw-------'; then
            : # Permissions are correct (600)
        else
            echo "  → Checksum file has weak permissions (should be 600)"
            PERMISSION_ISSUES=$((PERMISSION_ISSUES + 1))
        fi
    fi
fi

if [ $PERMISSION_ISSUES -eq 0 ]; then
    pass_test "All sensitive files have secure permissions (600)"
else
    fail_test "$PERMISSION_ISSUES files have insecure permissions"
fi
echo ""

# Summary
echo "================================================================"
echo "TEST SUMMARY"
echo "================================================================"
echo ""
echo -e "Tests passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Fix the issues above and run tests again."
    exit 1
fi
