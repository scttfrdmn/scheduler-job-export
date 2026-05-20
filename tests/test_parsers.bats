#!/usr/bin/env bats
# Unit tests for embedded Python parser blocks
# Each test extracts the parser from its script and runs it against fixture data.

load helpers.bash

setup() {
    TMPDIR=$(mktemp -d)
}

teardown() {
    rm -rf "$TMPDIR"
}

# ---------------------------------------------------------------------------
# Helper: extract and run a numbered Python block from a script
# Some scripts have multiple blocks; block_num selects which (1-based).
# ---------------------------------------------------------------------------
run_python_block() {
    local script="$1"
    local block_num="${2:-1}"
    shift 2
    local py_tmp="$TMPDIR/parser_${block_num}.py"

    # Extract the Nth python3 - ... << 'PYTHON_EOF' block
    awk -v target="$block_num" '
        /^python3 - / { count++; if (count == target) { found=1; next } }
        found && /^PYTHON_EOF/ { exit }
        found { print }
    ' "$REPO_ROOT/$script" > "$py_tmp"

    python3 "$py_tmp" "$@"
}

# ---------------------------------------------------------------------------
# SLURM: export_with_users.sh parser
# ---------------------------------------------------------------------------

@test "SLURM parser: produces output CSV from sacct fixture" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    [ -f "$TMPDIR/slurm_out.csv" ]
}

@test "SLURM parser: skips job step rows (.batch, .0)" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    # Fixture has 7 data rows but 1 is a .batch step — expect 6 output rows
    assert_csv_rows "$TMPDIR/slurm_out.csv" 6
}

@test "SLURM parser: maps user field correctly" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    assert_csv_field "$TMPDIR/slurm_out.csv" 1 user alice
}

@test "SLURM parser: detects GPU node type from AllocTRES" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    assert_csv_field "$TMPDIR/slurm_out.csv" 1 node_type gpu
}

@test "SLURM parser: extracts gpu_count from TRES" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    assert_csv_field "$TMPDIR/slurm_out.csv" 1 gpu_count 2
}

@test "SLURM parser: extracts gpu_types from TRES" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    assert_csv_field "$TMPDIR/slurm_out.csv" 1 gpu_types v100:2
}

@test "SLURM parser: multi-GPU types sorted descending by count" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    # Job 1004: gres/gpu:a100=2,gres/gpu:v100=2 — equal counts, alphabetical
    assert_csv_field "$TMPDIR/slurm_out.csv" 4 gpu_types "a100:2,v100:2"
}

@test "SLURM parser: compute job has empty gpu_count" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    # Job 1003 (carol preprocess) has no GPU
    assert_csv_field "$TMPDIR/slurm_out.csv" 3 gpu_count ""
}

@test "SLURM parser: compute job has node_type=compute" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    assert_csv_field "$TMPDIR/slurm_out.csv" 3 node_type compute
}

@test "SLURM parser: highmem partition gives node_type=highmem" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    # Job 1005 (eve) is in highmem partition
    assert_csv_field "$TMPDIR/slurm_out.csv" 5 node_type highmem
}

@test "SLURM parser: converts MaxRSS KB to MB" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    # Job 1001: MaxRSS=45231600K → 45231600/1024 = 44171 MB
    assert_csv_field "$TMPDIR/slurm_out.csv" 1 mem_used 44171
}

@test "SLURM parser: converts days-HH:MM:SS TotalCPU to seconds" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    # Job 1003: TotalCPU=1-02:30:00 → 86400+9000 = 95400 (stored as float 95400.0)
    assert_csv_field "$TMPDIR/slurm_out.csv" 3 cpu_time_used 95400.0
}

@test "SLURM parser: failed job has correct status" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    assert_csv_field "$TMPDIR/slurm_out.csv" 2 status FAILED
}

@test "SLURM parser: short job walltime correct" {
    run_python_block export_with_users.sh 1 \
        "$FIXTURES/slurm/sacct_parsable2.txt" \
        "$TMPDIR/slurm_out.csv"
    # Job 1006 (frank): Elapsed=00:00:30 → 30 seconds (stored as float 30.0)
    assert_csv_field "$TMPDIR/slurm_out.csv" 6 walltime_used 30.0
}

# ---------------------------------------------------------------------------
# LSF: export_lsf_comprehensive.sh parser
# ---------------------------------------------------------------------------

@test "LSF parser: produces output CSV from bhist fixture" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    [ -f "$TMPDIR/lsf_out.csv" ]
}

@test "LSF parser: parses 3 job records" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_rows "$TMPDIR/lsf_out.csv" 3
}

@test "LSF parser: maps user field" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_out.csv" 1 user alice
}

@test "LSF parser: maps group field" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_out.csv" 1 group physics
}

@test "LSF parser: maps queue field" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_out.csv" 1 queue gpu
}

@test "LSF parser: maps account from Project Name" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_out.csv" 1 account proj_a
}

@test "LSF parser: parses cpus_req from Processors Requested" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_out.csv" 1 cpus_req 16
}

@test "LSF parser: parses mem_req from Requested Resources" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_out.csv" 1 mem_req 65536
}

@test "LSF parser: parses MAX MEM to mem_used in MB" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_out.csv" 1 mem_used 44171
}

@test "LSF parser: EXIT job has correct status" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_out.csv" 2 status EXIT
}

@test "LSF parser: parses submit_time to ISO format" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_out.csv" 1 submit_time "2024-01-15 08:00:00"
}

@test "LSF parser: parses nodelist from Execution Hosts" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l.txt" \
        /dev/null \
        "$TMPDIR/lsf_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_out.csv" 1 nodelist gpu-node01
}

# ---------------------------------------------------------------------------
# LSF 9.x compatibility: Submit Time, Memory Utilized, Finish Time, Done,
# space-padded single-digit day dates
# ---------------------------------------------------------------------------

@test "LSF 9.x parser: handles Submit Time field name" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l_9x.txt" \
        /dev/null \
        "$TMPDIR/lsf_9x_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_9x_out.csv" 1 submit_time "2024-01-15 10:00:00"
}

@test "LSF 9.x parser: handles Memory Utilized field name" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l_9x.txt" \
        /dev/null \
        "$TMPDIR/lsf_9x_out.csv" \
        false
    # frank's job: Memory Utilized: 28672 MB
    assert_csv_field "$TMPDIR/lsf_9x_out.csv" 1 mem_used 28672
}

@test "LSF 9.x parser: handles Finish Time field name" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l_9x.txt" \
        /dev/null \
        "$TMPDIR/lsf_9x_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_9x_out.csv" 2 end_time "2024-01-01 09:03:45"
}

@test "LSF 9.x parser: handles Done field name" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l_9x.txt" \
        /dev/null \
        "$TMPDIR/lsf_9x_out.csv" \
        false
    assert_csv_field "$TMPDIR/lsf_9x_out.csv" 1 end_time "2024-01-15 12:02:15"
}

@test "LSF 9.x parser: handles space-padded single-digit day in date" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l_9x.txt" \
        /dev/null \
        "$TMPDIR/lsf_9x_out.csv" \
        false
    # grace's job: "Mon Jan  1 09:00:00 2024" — double-space before day
    assert_csv_field "$TMPDIR/lsf_9x_out.csv" 2 submit_time "2024-01-01 09:00:00"
}

@test "LSF 9.x parser: parses 2 job records" {
    run_python_block export_lsf_comprehensive.sh 1 \
        "$FIXTURES/lsf/bhist_l_9x.txt" \
        /dev/null \
        "$TMPDIR/lsf_9x_out.csv" \
        false
    assert_csv_rows "$TMPDIR/lsf_9x_out.csv" 2
}

# ---------------------------------------------------------------------------
# LSF: export_lsf_cluster_config.sh parser (bhosts + lshosts)
# ---------------------------------------------------------------------------

@test "LSF cluster config parser: produces CSV from bhosts+lshosts fixtures" {
    run_python_block export_lsf_cluster_config.sh 1 \
        "$FIXTURES/lsf/bhosts_w.txt" \
        "$FIXTURES/lsf/lshosts_w.txt" \
        /dev/null \
        "$TMPDIR/lsf_config.csv"
    [ -f "$TMPDIR/lsf_config.csv" ]
}

@test "LSF cluster config parser: parses 8 hosts" {
    run_python_block export_lsf_cluster_config.sh 1 \
        "$FIXTURES/lsf/bhosts_w.txt" \
        "$FIXTURES/lsf/lshosts_w.txt" \
        /dev/null \
        "$TMPDIR/lsf_config.csv"
    assert_csv_rows "$TMPDIR/lsf_config.csv" 8
}

@test "LSF cluster config parser: enriches CPU count from lshosts" {
    run_python_block export_lsf_cluster_config.sh 1 \
        "$FIXTURES/lsf/bhosts_w.txt" \
        "$FIXTURES/lsf/lshosts_w.txt" \
        /dev/null \
        "$TMPDIR/lsf_config.csv"
    # gpu-node01: lshosts shows ncpus=32
    assert_csv_field "$TMPDIR/lsf_config.csv" 1 cpus 32
}

@test "LSF cluster config parser: enriches memory_mb from lshosts" {
    run_python_block export_lsf_cluster_config.sh 1 \
        "$FIXTURES/lsf/bhosts_w.txt" \
        "$FIXTURES/lsf/lshosts_w.txt" \
        /dev/null \
        "$TMPDIR/lsf_config.csv"
    assert_csv_field "$TMPDIR/lsf_config.csv" 1 memory_mb 262144
}

@test "LSF 9.x cluster config parser: handles 7-column lshosts (no ncores/nthreads)" {
    run_python_block export_lsf_cluster_config.sh 1 \
        "$FIXTURES/lsf/bhosts_w.txt" \
        "$FIXTURES/lsf/lshosts_w_9x.txt" \
        /dev/null \
        "$TMPDIR/lsf_config_9x.csv"
    [ -f "$TMPDIR/lsf_config_9x.csv" ]
    # gpu-node01: ncpus=32, memory=262144 from 7-col format
    assert_csv_field "$TMPDIR/lsf_config_9x.csv" 1 cpus 32
    assert_csv_field "$TMPDIR/lsf_config_9x.csv" 1 memory_mb 262144
}

# ---------------------------------------------------------------------------
# PBS: export_pbs_data.sh parser
# ---------------------------------------------------------------------------

@test "PBS parser: produces output CSV from accounting log fixture" {
    run_python_block export_pbs_data.sh 1 \
        "$FIXTURES/pbs" \
        "20240115" \
        "20240115" \
        "$TMPDIR/pbs_out.csv"
    [ -f "$TMPDIR/pbs_out.csv" ]
}

@test "PBS parser: parses 3 completed/exited jobs" {
    run_python_block export_pbs_data.sh 1 \
        "$FIXTURES/pbs" \
        "20240115" \
        "20240115" \
        "$TMPDIR/pbs_out.csv"
    assert_csv_rows "$TMPDIR/pbs_out.csv" 3
}

@test "PBS parser: maps user field" {
    run_python_block export_pbs_data.sh 1 \
        "$FIXTURES/pbs" \
        "20240115" \
        "20240115" \
        "$TMPDIR/pbs_out.csv"
    assert_csv_field "$TMPDIR/pbs_out.csv" 1 user alice
}

@test "PBS parser: maps exit_status 0 for successful job" {
    run_python_block export_pbs_data.sh 1 \
        "$FIXTURES/pbs" \
        "20240115" \
        "20240115" \
        "$TMPDIR/pbs_out.csv"
    assert_csv_field "$TMPDIR/pbs_out.csv" 1 exit_status 0
}

@test "PBS parser: maps exit_status 1 for failed job" {
    run_python_block export_pbs_data.sh 1 \
        "$FIXTURES/pbs" \
        "20240115" \
        "20240115" \
        "$TMPDIR/pbs_out.csv"
    assert_csv_field "$TMPDIR/pbs_out.csv" 2 exit_status 1
}

# ---------------------------------------------------------------------------
# UGE: export_uge_data.sh parser
# ---------------------------------------------------------------------------

@test "UGE parser: produces output CSV from qacct fixture" {
    run_python_block export_uge_data.sh 1 \
        "$FIXTURES/uge/qacct.txt" \
        "$TMPDIR/uge_out.csv"
    [ -f "$TMPDIR/uge_out.csv" ]
}

@test "UGE parser: parses 3 job records" {
    run_python_block export_uge_data.sh 1 \
        "$FIXTURES/uge/qacct.txt" \
        "$TMPDIR/uge_out.csv"
    assert_csv_rows "$TMPDIR/uge_out.csv" 3
}

@test "UGE parser: maps owner to user field" {
    run_python_block export_uge_data.sh 1 \
        "$FIXTURES/uge/qacct.txt" \
        "$TMPDIR/uge_out.csv"
    assert_csv_field "$TMPDIR/uge_out.csv" 1 user alice
}

@test "UGE parser: maps group field" {
    run_python_block export_uge_data.sh 1 \
        "$FIXTURES/uge/qacct.txt" \
        "$TMPDIR/uge_out.csv"
    assert_csv_field "$TMPDIR/uge_out.csv" 1 group physics
}

@test "UGE parser: maps slots field" {
    run_python_block export_uge_data.sh 1 \
        "$FIXTURES/uge/qacct.txt" \
        "$TMPDIR/uge_out.csv"
    # UGE parser uses 'slots' column name (not 'cpus')
    assert_csv_field "$TMPDIR/uge_out.csv" 1 slots 16
}

@test "UGE parser: maps exit_status" {
    run_python_block export_uge_data.sh 1 \
        "$FIXTURES/uge/qacct.txt" \
        "$TMPDIR/uge_out.csv"
    assert_csv_field "$TMPDIR/uge_out.csv" 2 exit_status 1
}

@test "UGE parser: maps queue name" {
    run_python_block export_uge_data.sh 1 \
        "$FIXTURES/uge/qacct.txt" \
        "$TMPDIR/uge_out.csv"
    assert_csv_field "$TMPDIR/uge_out.csv" 1 queue gpu.q
}

# ---------------------------------------------------------------------------
# HTCondor: export_htcondor_data.sh parser
# ---------------------------------------------------------------------------

@test "HTCondor parser: produces output CSV from condor_history fixture" {
    run_python_block export_htcondor_data.sh 1 \
        "$FIXTURES/htcondor/condor_history.txt" \
        "$TMPDIR/condor_out.csv"
    [ -f "$TMPDIR/condor_out.csv" ]
}

@test "HTCondor parser: parses 6 job records" {
    run_python_block export_htcondor_data.sh 1 \
        "$FIXTURES/htcondor/condor_history.txt" \
        "$TMPDIR/condor_out.csv"
    assert_csv_rows "$TMPDIR/condor_out.csv" 6
}

@test "HTCondor parser: maps Owner to user" {
    run_python_block export_htcondor_data.sh 1 \
        "$FIXTURES/htcondor/condor_history.txt" \
        "$TMPDIR/condor_out.csv"
    assert_csv_field "$TMPDIR/condor_out.csv" 1 user alice
}

@test "HTCondor parser: sets account from AcctGroup" {
    run_python_block export_htcondor_data.sh 1 \
        "$FIXTURES/htcondor/condor_history.txt" \
        "$TMPDIR/condor_out.csv"
    assert_csv_field "$TMPDIR/condor_out.csv" 1 account "physics.alice"
}

@test "HTCondor parser: extracts group from AccountingGroup dot-notation" {
    run_python_block export_htcondor_data.sh 1 \
        "$FIXTURES/htcondor/condor_history.txt" \
        "$TMPDIR/condor_out.csv"
    # AccountingGroup=physics.alice → group=physics
    assert_csv_field "$TMPDIR/condor_out.csv" 1 group physics
}

@test "HTCondor parser: maps RequestCpus to cpus_req" {
    run_python_block export_htcondor_data.sh 1 \
        "$FIXTURES/htcondor/condor_history.txt" \
        "$TMPDIR/condor_out.csv"
    assert_csv_field "$TMPDIR/condor_out.csv" 1 cpus_req 16
}

@test "HTCondor parser: maps RequestMemory to mem_req" {
    run_python_block export_htcondor_data.sh 1 \
        "$FIXTURES/htcondor/condor_history.txt" \
        "$TMPDIR/condor_out.csv"
    assert_csv_field "$TMPDIR/condor_out.csv" 1 mem_req 65536
}

@test "HTCondor parser: maps ClusterId.ProcId to job_id" {
    run_python_block export_htcondor_data.sh 1 \
        "$FIXTURES/htcondor/condor_history.txt" \
        "$TMPDIR/condor_out.csv"
    assert_csv_field "$TMPDIR/condor_out.csv" 1 job_id "1001.0"
}
