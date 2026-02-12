#!/bin/bash
#
# Python Linting for Scheduler Export Scripts
#
# This script extracts embedded Python code from bash scripts and runs linting.
#

set -euo pipefail

echo "================================================================"
echo "Python Code Linting - Scheduler Data Export"
echo "================================================================"
echo ""

# Check if ruff is installed
if ! command -v ruff &> /dev/null; then
    echo "ERROR: ruff is not installed"
    echo ""
    echo "Install with:"
    echo "  pip install ruff"
    echo "  # or"
    echo "  pip3 install ruff"
    echo "  # or"
    echo "  pipx install ruff"
    echo ""
    exit 1
fi

echo "✓ Found ruff: $(ruff --version)"
echo ""

# Create temp directory for extracted Python code
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

echo "Extracting Python code from bash scripts..."
echo ""

# Counter for scripts processed
SCRIPTS_FOUND=0
PYTHON_BLOCKS=0
LINT_ERRORS=0

# Function to extract Python code from bash script
extract_python() {
    local bash_script="$1"
    local output_dir="$2"

    # Extract Python heredoc blocks
    # Pattern: python3 << 'PYTHON_EOF' ... PYTHON_EOF

    local in_python=0
    local python_block=""
    local block_num=0

    while IFS= read -r line; do
        # Start of Python block
        if [[ "$line" =~ python3[[:space:]]*\<\<[[:space:]]*[\'\"]*PYTHON_EOF[\'\"]*[[:space:]]*$ ]]; then
            in_python=1
            python_block=""
            continue
        fi

        # End of Python block
        if [[ "$line" =~ ^PYTHON_EOF[[:space:]]*$ ]] && [ $in_python -eq 1 ]; then
            in_python=0
            block_num=$((block_num + 1))

            # Write Python block to file
            local basename=$(basename "$bash_script" .sh)
            local output_file="$output_dir/${basename}_block${block_num}.py"
            echo "$python_block" > "$output_file"

            echo "  ├─ Block $block_num: ${basename}_block${block_num}.py"
            PYTHON_BLOCKS=$((PYTHON_BLOCKS + 1))

            python_block=""
            continue
        fi

        # Inside Python block - collect lines
        if [ $in_python -eq 1 ]; then
            python_block="${python_block}${line}"$'\n'
        fi
    done < "$bash_script"

    return $block_num
}

# Process all export scripts
for script in export_*.sh anonymize_cluster_data.sh; do
    if [ ! -f "$script" ]; then
        continue
    fi

    echo "Processing: $script"
    SCRIPTS_FOUND=$((SCRIPTS_FOUND + 1))

    extract_python "$script" "$TEMP_DIR"
    echo ""
done

# Also check standalone Python files
if [ -f "standardize_cluster_config.py" ]; then
    echo "Processing: standardize_cluster_config.py (standalone)"
    cp standardize_cluster_config.py "$TEMP_DIR/"
    PYTHON_BLOCKS=$((PYTHON_BLOCKS + 1))
    echo "  └─ Copied standalone Python file"
    echo ""
fi

echo "================================================================"
echo "EXTRACTION COMPLETE"
echo "================================================================"
echo ""
echo "Bash scripts processed: $SCRIPTS_FOUND"
echo "Python blocks extracted: $PYTHON_BLOCKS"
echo ""

if [ $PYTHON_BLOCKS -eq 0 ]; then
    echo "WARNING: No Python code found to lint!"
    exit 0
fi

echo "================================================================"
echo "RUNNING LINTER"
echo "================================================================"
echo ""

# Run ruff on extracted Python files
if ruff check "$TEMP_DIR" --config pyproject.toml; then
    echo ""
    echo "================================================================"
    echo "✓ ALL CHECKS PASSED"
    echo "================================================================"
    echo ""
    echo "No linting errors found in $PYTHON_BLOCKS Python code blocks!"
    exit 0
else
    LINT_ERRORS=$?
    echo ""
    echo "================================================================"
    echo "✗ LINTING ERRORS FOUND"
    echo "================================================================"
    echo ""
    echo "Found issues in extracted Python code."
    echo ""
    echo "To see detailed output, extracted files are in: $TEMP_DIR"
    echo "(They will be deleted when this script exits)"
    echo ""
    echo "To fix issues automatically where possible:"
    echo "  ruff check $TEMP_DIR --fix"
    echo ""
    exit $LINT_ERRORS
fi
