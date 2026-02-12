#!/bin/bash
#
# Run ShellCheck Bash Security Linter
#
# Scans all bash scripts for security issues and best practice violations.
#

set -euo pipefail

echo "================================================================"
echo "ShellCheck Bash Security Linter"
echo "================================================================"
echo ""

# Check if shellcheck is installed
if ! command -v shellcheck &> /dev/null; then
    echo "ERROR: shellcheck is not installed"
    echo ""
    echo "Install with:"
    echo "  # macOS"
    echo "  brew install shellcheck"
    echo ""
    echo "  # Ubuntu/Debian"
    echo "  apt-get install shellcheck"
    echo ""
    echo "  # Or download from: https://www.shellcheck.net/"
    echo ""
    exit 1
fi

echo "✓ Found shellcheck: $(shellcheck --version | head -2 | tail -1)"
echo ""

# Find all bash scripts
echo "Finding bash scripts..."
SCRIPTS=$(find . -name "*.sh" -not -path "./.git/*" -not -path "./venv/*" -not -path "./.venv/*")

if [ -z "$SCRIPTS" ]; then
    echo "No bash scripts found"
    exit 0
fi

echo "Found bash scripts:"
echo "$SCRIPTS" | sed 's/^/  /'
echo ""
echo "Running ShellCheck..."
echo ""

# Run shellcheck on all scripts
ERRORS=0
WARNINGS=0
PASSED=0

for script in $SCRIPTS; do
    echo "Checking: $script"

    # Run shellcheck and capture output
    if shellcheck "$script"; then
        PASSED=$((PASSED + 1))
    else
        exit_code=$?
        if [ $exit_code -eq 1 ]; then
            ERRORS=$((ERRORS + 1))
        else
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
    echo ""
done

echo "================================================================"
echo "ShellCheck Results"
echo "================================================================"
echo ""
echo "Scripts checked: $(echo "$SCRIPTS" | wc -l | tr -d ' ')"
echo "Passed: $PASSED"
echo "Warnings: $WARNINGS"
echo "Errors: $ERRORS"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo "✓ All scripts passed ShellCheck"
    exit 0
else
    echo "✗ Some scripts have ShellCheck errors"
    exit 1
fi
