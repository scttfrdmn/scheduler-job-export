#!/usr/bin/env bats
# Integration tests: run export scripts end-to-end with mocked scheduler commands.
# Scheduler binaries are replaced with shell functions that return fixture data.

load helpers.bash

setup() {
    TEST_DIR=$(mktemp -d)
    # Run all scripts from a temp working directory so output CSVs land there
    cd "$TEST_DIR"

    # Copy required library files into the working directory
    cp "$REPO_ROOT/validation.sh" .
    cp "$REPO_ROOT/security_logging.sh" .

    # Suppress security log writes during tests
    export SECURITY_LOG="$TEST_DIR/test_security.log"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ---------------------------------------------------------------------------
# Helpers to inject mock scheduler commands into PATH
# ---------------------------------------------------------------------------

mock_sacct() {
    local mock_dir="$TEST_DIR/mock_bin"
    mkdir -p "$mock_dir"
    cat > "$mock_dir/sacct" << MOCK
#!/bin/bash
cat "$FIXTURES/slurm/sacct_parsable2.txt"
MOCK
    chmod +x "$mock_dir/sacct"
    export PATH="$mock_dir:$PATH"
}

mock_bhist() {
    local mock_dir="$TEST_DIR/mock_bin"
    mkdir -p "$mock_dir"
    # bhist with -a flag falls back silently; provide fixture on stdout
    cat > "$mock_dir/bhist" << MOCK
#!/bin/bash
cat "$FIXTURES/lsf/bhist_l.txt"
MOCK
    chmod +x "$mock_dir/bhist"
    # bacct doesn't exist in fixture env, so omit it to trigger the fallback
    export PATH="$mock_dir:$PATH"
}

mock_bhosts_lshosts() {
    local mock_dir="$TEST_DIR/mock_bin"
    mkdir -p "$mock_dir"
    cat > "$mock_dir/bhosts" << MOCK
#!/bin/bash
if [[ "\$*" == *"-l"* ]]; then
    echo ""   # bhosts -l detail: empty is fine, parser handles it gracefully
else
    cat "$FIXTURES/lsf/bhosts_w.txt"
fi
MOCK
    cat > "$mock_dir/lshosts" << MOCK
#!/bin/bash
cat "$FIXTURES/lsf/lshosts_w.txt"
MOCK
    chmod +x "$mock_dir/bhosts" "$mock_dir/lshosts"
    export PATH="$mock_dir:$PATH"
}

mock_qacct() {
    local mock_dir="$TEST_DIR/mock_bin"
    mkdir -p "$mock_dir"
    cat > "$mock_dir/qacct" << MOCK
#!/bin/bash
cat "$FIXTURES/uge/qacct.txt"
MOCK
    chmod +x "$mock_dir/qacct"
    export PATH="$mock_dir:$PATH"
}

mock_qstat() {
    # PBS parses accounting files directly; qstat only needs to exist so the
    # script's "which PBS command is available" gate passes.
    local mock_dir="$TEST_DIR/mock_bin"
    mkdir -p "$mock_dir"
    cat > "$mock_dir/qstat" << MOCK
#!/bin/bash
exit 0
MOCK
    chmod +x "$mock_dir/qstat"
    export PATH="$mock_dir:$PATH"
}

mock_condor_history() {
    local mock_dir="$TEST_DIR/mock_bin"
    mkdir -p "$mock_dir"
    cat > "$mock_dir/condor_history" << MOCK
#!/bin/bash
cat "$FIXTURES/htcondor/condor_history.txt"
MOCK
    chmod +x "$mock_dir/condor_history"
    export PATH="$mock_dir:$PATH"
}

# ---------------------------------------------------------------------------
# SLURM: export_with_users.sh
# ---------------------------------------------------------------------------

@test "SLURM export_with_users: runs end-to-end and produces CSV" {
    mock_sacct
    PATH="$TEST_DIR/mock_bin:$PATH" bash "$REPO_ROOT/export_with_users.sh" 2024-01-15 2024-01-15 >/dev/null 2>&1
    csv_file=$(ls slurm_jobs_with_users_*.csv 2>/dev/null | head -1)
    [ -n "$csv_file" ]
    [ -f "$csv_file" ]
}

@test "SLURM export_with_users: output has correct headers" {
    mock_sacct
    PATH="$TEST_DIR/mock_bin:$PATH" bash "$REPO_ROOT/export_with_users.sh" 2024-01-15 2024-01-15 >/dev/null 2>&1
    csv_file=$(ls slurm_jobs_with_users_*.csv 2>/dev/null | head -1)
    header=$(head -1 "$csv_file")
    [[ "$header" == *"user"* ]]
    [[ "$header" == *"gpu_count"* ]]
    [[ "$header" == *"node_type"* ]]
}

@test "SLURM export_with_users: rejects injection in start date" {
    run bash "$REPO_ROOT/export_with_users.sh" '$(whoami)' 2024-01-15
    [ "$status" -ne 0 ]
}

@test "SLURM export_with_users: rejects invalid date format" {
    run bash "$REPO_ROOT/export_with_users.sh" "2024/01/15" "2024/01/15"
    [ "$status" -ne 0 ]
}

@test "SLURM export_with_users: creates sha256 checksum file" {
    mock_sacct
    PATH="$TEST_DIR/mock_bin:$PATH" bash "$REPO_ROOT/export_with_users.sh" 2024-01-15 2024-01-15 >/dev/null 2>&1
    csv_file=$(ls slurm_jobs_with_users_*.csv 2>/dev/null | head -1)
    [ -f "${csv_file}.sha256" ]
}

# ---------------------------------------------------------------------------
# LSF: export_lsf_comprehensive.sh
# ---------------------------------------------------------------------------

@test "LSF export_lsf_comprehensive: runs end-to-end and produces CSV" {
    mock_bhist
    run bash "$REPO_ROOT/export_lsf_comprehensive.sh" 2024/01/15 2024/01/15
    [ "$status" -eq 0 ]
    csv_file=$(ls lsf_jobs_with_users_*.csv 2>/dev/null | head -1)
    [ -n "$csv_file" ]
}

@test "LSF export_lsf_comprehensive: rejects injection in start date" {
    mock_bhist
    run bash "$REPO_ROOT/export_lsf_comprehensive.sh" '2024/01/01;whoami' 2024/01/15
    [ "$status" -ne 0 ]
}

@test "LSF export_lsf_comprehensive: rejects SLURM-format date" {
    mock_bhist
    run bash "$REPO_ROOT/export_lsf_comprehensive.sh" "2024-01-15" "2024-01-15"
    [ "$status" -ne 0 ]
}

# ---------------------------------------------------------------------------
# LSF: export_lsf_cluster_config.sh
# ---------------------------------------------------------------------------

@test "LSF export_lsf_cluster_config: runs end-to-end and produces CSV" {
    mock_bhosts_lshosts
    run bash "$REPO_ROOT/export_lsf_cluster_config.sh"
    [ "$status" -eq 0 ]
    csv_file=$(ls lsf_cluster_config_*.csv 2>/dev/null | head -1)
    [ -n "$csv_file" ]
}

@test "LSF export_lsf_cluster_config: output CSV has hostname column" {
    mock_bhosts_lshosts
    bash "$REPO_ROOT/export_lsf_cluster_config.sh" >/dev/null 2>&1
    csv_file=$(ls lsf_cluster_config_*.csv 2>/dev/null | head -1)
    header=$(head -1 "$csv_file")
    [[ "$header" == *"hostname"* ]]
}

# ---------------------------------------------------------------------------
# UGE: export_uge_data.sh
# ---------------------------------------------------------------------------

@test "UGE export_uge_data: runs end-to-end and produces CSV" {
    mock_qacct
    run bash "$REPO_ROOT/export_uge_data.sh" 01/15/2024 01/15/2024
    [ "$status" -eq 0 ]
    csv_file=$(ls uge_jobs_*.csv 2>/dev/null | head -1)
    [ -n "$csv_file" ]
}

@test "UGE export_uge_data: output has user column" {
    mock_qacct
    PATH="$TEST_DIR/mock_bin:$PATH" bash "$REPO_ROOT/export_uge_data.sh" 01/15/2024 01/15/2024 >/dev/null 2>&1
    csv_file=$(ls uge_jobs_*.csv 2>/dev/null | head -1)
    header=$(head -1 "$csv_file")
    [[ "$header" == *"user"* ]]
}

# ---------------------------------------------------------------------------
# HTCondor: export_htcondor_data.sh
# ---------------------------------------------------------------------------

@test "HTCondor export_htcondor_data: runs end-to-end and produces CSV" {
    mock_condor_history
    run bash "$REPO_ROOT/export_htcondor_data.sh"
    [ "$status" -eq 0 ]
    csv_file=$(ls htcondor_jobs_*.csv 2>/dev/null | head -1)
    [ -n "$csv_file" ]
}

@test "HTCondor export_htcondor_data: output has correct headers" {
    mock_condor_history
    bash "$REPO_ROOT/export_htcondor_data.sh" >/dev/null 2>&1
    csv_file=$(ls htcondor_jobs_*.csv 2>/dev/null | head -1)
    header=$(head -1 "$csv_file")
    [[ "$header" == *"user"* ]]
    [[ "$header" == *"job_id"* ]]
    [[ "$header" == *"cpus_req"* ]]
}

# ---------------------------------------------------------------------------
# PBS: export_pbs_data.sh
# ---------------------------------------------------------------------------
# PBS reads accounting files from a directory rather than a mocked binary, so
# the fixture directory is injected via PBS_ACCT_DIR (honored by the script).
# The fixture dir contains an accounting file named 20240115, hence the date
# range below.

@test "PBS export_pbs_data: runs end-to-end and produces CSV" {
    mock_qstat
    run env PBS_ACCT_DIR="$FIXTURES/pbs" bash "$REPO_ROOT/export_pbs_data.sh" 20240115 20240115
    [ "$status" -eq 0 ]
    csv_file=$(ls pbs_jobs_*.csv 2>/dev/null | head -1)
    [ -n "$csv_file" ]
}

@test "PBS export_pbs_data: output CSV has expected header" {
    mock_qstat
    PBS_ACCT_DIR="$FIXTURES/pbs" bash "$REPO_ROOT/export_pbs_data.sh" 20240115 20240115 >/dev/null 2>&1
    csv_file=$(ls pbs_jobs_*.csv 2>/dev/null | head -1)
    header=$(head -1 "$csv_file")
    [[ "$header" == *"user"* ]]
    [[ "$header" == *"job_id"* ]]
    [[ "$header" == *"scheduler"* ]]
}

# ---------------------------------------------------------------------------
# Anonymization: end-to-end with SLURM output
# ---------------------------------------------------------------------------

@test "anonymize: transforms SLURM CSV output correctly" {
    mock_sacct
    PATH="$TEST_DIR/mock_bin:$PATH" bash "$REPO_ROOT/export_with_users.sh" 2024-01-15 2024-01-15 >/dev/null 2>&1
    csv_file=$(ls slurm_jobs_with_users_*.csv 2>/dev/null | head -1)

    run bash "$REPO_ROOT/anonymize_cluster_data.sh" \
        "$csv_file" \
        "$TEST_DIR/anon_out.csv" \
        "$TEST_DIR/mapping.txt"
    [ "$status" -eq 0 ]
    [ -f "$TEST_DIR/anon_out.csv" ]
}

@test "anonymize: mapping file has secure permissions (600)" {
    mock_sacct
    PATH="$TEST_DIR/mock_bin:$PATH" bash "$REPO_ROOT/export_with_users.sh" 2024-01-15 2024-01-15 >/dev/null 2>&1
    csv_file=$(ls slurm_jobs_with_users_*.csv 2>/dev/null | head -1)
    bash "$REPO_ROOT/anonymize_cluster_data.sh" \
        "$csv_file" \
        "$TEST_DIR/anon_out.csv" \
        "$TEST_DIR/mapping.txt" >/dev/null 2>&1
    perms=$(ls -l "$TEST_DIR/mapping.txt" | cut -c1-10)
    [ "$perms" = "-rw-------" ]
}

@test "anonymize: original usernames not present in anonymized output" {
    mock_sacct
    PATH="$TEST_DIR/mock_bin:$PATH" bash "$REPO_ROOT/export_with_users.sh" 2024-01-15 2024-01-15 >/dev/null 2>&1
    csv_file=$(ls slurm_jobs_with_users_*.csv 2>/dev/null | head -1)
    bash "$REPO_ROOT/anonymize_cluster_data.sh" \
        "$csv_file" \
        "$TEST_DIR/anon_out.csv" \
        "$TEST_DIR/mapping.txt" >/dev/null 2>&1
    ! grep -q "^alice," "$TEST_DIR/anon_out.csv"
    ! grep -q ",alice," "$TEST_DIR/anon_out.csv"
}
