# Shared helpers for all bats test files

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURES="$REPO_ROOT/tests/fixtures"

# Source the script under test from the repo root
load_validation() {
    source "$REPO_ROOT/validation.sh"
}

# Run a Python heredoc block extracted from an export script directly,
# passing fixture files in place of real scheduler output.
# Usage: run_python_parser <script> <fixture_file> [extra_args...]
#   Extracts the first PYTHON_EOF block from <script>, writes it to a
#   temp file, and runs it with the provided arguments.
run_python_parser() {
    local script="$1"; shift
    local py_tmp
    py_tmp=$(mktemp /tmp/bats_parser_XXXXXX.py)

    # Extract the Python block (everything between the first python3 - ... << 'PYTHON_EOF' and PYTHON_EOF)
    awk '/^python3 - /{found=1; next} found && /^PYTHON_EOF/{exit} found{print}' "$REPO_ROOT/$script" > "$py_tmp"

    python3 "$py_tmp" "$@"
    local rc=$?
    rm -f "$py_tmp"
    return $rc
}

# Assert a CSV output file has exactly N data rows (not counting header)
assert_csv_rows() {
    local file="$1"
    local expected="$2"
    local actual
    actual=$(tail -n +2 "$file" | grep -c '.' || true)
    if [[ "$actual" -ne "$expected" ]]; then
        echo "Expected $expected rows in $file, got $actual" >&2
        return 1
    fi
}

# Assert a CSV field value in a specific row and column by name.
# Uses Python's csv module to handle values that contain commas.
assert_csv_field() {
    local file="$1"
    local row="$2"      # 1-based data row (not counting header)
    local col_name="$3"
    local expected="$4"

    local actual
    actual=$(python3 - "$file" "$row" "$col_name" << 'PYEOF'
import csv, sys
path, row, col = sys.argv[1], int(sys.argv[2]), sys.argv[3]
with open(path) as f:
    reader = csv.DictReader(f)
    rows = list(reader)
if col not in reader.fieldnames:
    print(f"NOTFOUND:{col}", end="")
    sys.exit(1)
if row > len(rows):
    print(f"ROWMISSING:{row}", end="")
    sys.exit(1)
print(rows[row - 1].get(col, ""), end="")
PYEOF
)
    local rc=$?
    if [[ $rc -ne 0 ]]; then
        echo "${actual}" >&2
        return 1
    fi
    if [[ "$actual" != "$expected" ]]; then
        echo "Row $row, col '$col_name': expected '$expected', got '$actual'" >&2
        return 1
    fi
}
