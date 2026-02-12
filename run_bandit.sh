#!/bin/bash
#
# Run Bandit Python Security Scanner
#
# Scans Python code for security issues using Bandit.
#

set -euo pipefail

echo "================================================================"
echo "Bandit Python Security Scanner"
echo "================================================================"
echo ""

# Check if bandit is installed
if ! command -v bandit &> /dev/null; then
    echo "ERROR: bandit is not installed"
    echo ""
    echo "Install with:"
    echo "  pip install bandit"
    echo "  # or"
    echo "  pip3 install bandit"
    echo "  # or"
    echo "  pipx install bandit"
    echo ""
    exit 1
fi

echo "✓ Found bandit: $(bandit --version 2>&1 | head -1)"
echo ""

# Scan standalone Python files
echo "Scanning Python files..."
echo ""

PYTHON_FILES=$(find . -name "*.py" -not -path "./.git/*" -not -path "./venv/*" -not -path "./.venv/*")

if [ -z "$PYTHON_FILES" ]; then
    echo "No Python files found to scan"
else
    echo "Found Python files:"
    echo "$PYTHON_FILES" | sed 's/^/  /'
    echo ""

    bandit -c .bandit -r . -f screen
fi

echo ""
echo "================================================================"
echo "Bandit scan complete"
echo "================================================================"
