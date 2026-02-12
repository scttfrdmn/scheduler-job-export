#!/bin/bash
#
# Run All Quality Checks
#
# Runs tests and linting for the scheduler export scripts
#

set -euo pipefail

echo "================================================================"
echo "Quality Checks - Scheduler Data Export"
echo "================================================================"
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0

# Run tests
echo "Step 1: Running test harness..."
echo "================================================================"
echo ""

if ./test_exports.sh; then
    echo ""
    echo "✓ Tests passed"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo ""
    echo "✗ Tests failed"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
fi

echo ""
echo ""

# Run Python linting (optional - only if ruff is installed)
echo "Step 2: Running Python linter..."
echo "================================================================"
echo ""

if command -v ruff &> /dev/null; then
    if ./lint_python.sh; then
        echo ""
        echo "✓ Linting passed"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo ""
        echo "✗ Linting failed"
        CHECKS_FAILED=$((CHECKS_FAILED + 1))
    fi
else
    echo "⊘ Skipping linting (ruff not installed)"
    echo ""
    echo "To install ruff:"
    echo "  pip install ruff"
    echo "  # or"
    echo "  pipx install ruff"
    echo ""
fi

echo ""
echo "================================================================"
echo "FINAL SUMMARY"
echo "================================================================"
echo ""
echo "Checks passed: $CHECKS_PASSED"
echo "Checks failed: $CHECKS_FAILED"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo "✓ ALL QUALITY CHECKS PASSED"
    exit 0
else
    echo "✗ SOME CHECKS FAILED"
    echo ""
    echo "Please fix the issues above before committing."
    exit 1
fi
