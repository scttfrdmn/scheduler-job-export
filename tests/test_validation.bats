#!/usr/bin/env bats
# Unit tests for validation.sh

load helpers.bash
load_validation

# ---------------------------------------------------------------------------
# validate_date_slurm
# ---------------------------------------------------------------------------

@test "validate_date_slurm: accepts valid date" {
    run validate_date_slurm "2024-01-15"
    [ "$status" -eq 0 ]
}

@test "validate_date_slurm: rejects wrong separator" {
    run validate_date_slurm "2024/01/15"
    [ "$status" -ne 0 ]
}

@test "validate_date_slurm: rejects month 00" {
    run validate_date_slurm "2024-00-15"
    [ "$status" -ne 0 ]
}

@test "validate_date_slurm: rejects month 13" {
    run validate_date_slurm "2024-13-01"
    [ "$status" -ne 0 ]
}

@test "validate_date_slurm: rejects day 00" {
    run validate_date_slurm "2024-01-00"
    [ "$status" -ne 0 ]
}

@test "validate_date_slurm: rejects day 32" {
    run validate_date_slurm "2024-01-32"
    [ "$status" -ne 0 ]
}

@test "validate_date_slurm: rejects year before 2000" {
    run validate_date_slurm "1999-12-31"
    [ "$status" -ne 0 ]
}

@test "validate_date_slurm: rejects year after 2099" {
    run validate_date_slurm "2100-01-01"
    [ "$status" -ne 0 ]
}

@test "validate_date_slurm: accepts boundary year 2000" {
    run validate_date_slurm "2000-01-01"
    [ "$status" -eq 0 ]
}

@test "validate_date_slurm: accepts boundary year 2099" {
    run validate_date_slurm "2099-12-31"
    [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# validate_date_lsf
# ---------------------------------------------------------------------------

@test "validate_date_lsf: accepts valid date" {
    run validate_date_lsf "2024/01/15"
    [ "$status" -eq 0 ]
}

@test "validate_date_lsf: rejects dash separator" {
    run validate_date_lsf "2024-01-15"
    [ "$status" -ne 0 ]
}

@test "validate_date_lsf: rejects month 13" {
    run validate_date_lsf "2024/13/01"
    [ "$status" -ne 0 ]
}

@test "validate_date_lsf: rejects day 32" {
    run validate_date_lsf "2024/01/32"
    [ "$status" -ne 0 ]
}

# ---------------------------------------------------------------------------
# validate_date_pbs
# ---------------------------------------------------------------------------

@test "validate_date_pbs: accepts valid date" {
    run validate_date_pbs "20240115"
    [ "$status" -eq 0 ]
}

@test "validate_date_pbs: rejects date with separator" {
    run validate_date_pbs "2024-01-15"
    [ "$status" -ne 0 ]
}

@test "validate_date_pbs: rejects 7-digit input" {
    run validate_date_pbs "2024011"
    [ "$status" -ne 0 ]
}

@test "validate_date_pbs: rejects month 00" {
    run validate_date_pbs "20240001"
    [ "$status" -ne 0 ]
}

# ---------------------------------------------------------------------------
# validate_date_uge
# ---------------------------------------------------------------------------

@test "validate_date_uge: accepts valid date" {
    run validate_date_uge "01/15/2024"
    [ "$status" -eq 0 ]
}

@test "validate_date_uge: rejects YYYY/MM/DD order" {
    run validate_date_uge "2024/01/15"
    [ "$status" -ne 0 ]
}

@test "validate_date_uge: rejects month 13" {
    run validate_date_uge "13/15/2024"
    [ "$status" -ne 0 ]
}

# ---------------------------------------------------------------------------
# detect_injection_attempt
# ---------------------------------------------------------------------------

@test "detect_injection_attempt: clean date returns non-zero (not detected)" {
    run detect_injection_attempt "2024-01-15"
    [ "$status" -ne 0 ]
}

@test "detect_injection_attempt: \$() substitution detected" {
    run detect_injection_attempt '$(whoami)'
    [ "$status" -eq 0 ]
}

@test "detect_injection_attempt: backtick substitution detected" {
    run detect_injection_attempt '`cat /etc/passwd`'
    [ "$status" -eq 0 ]
}

@test "detect_injection_attempt: semicolon detected" {
    run detect_injection_attempt '2024-01-01; rm -rf /'
    [ "$status" -eq 0 ]
}

@test "detect_injection_attempt: pipe detected" {
    run detect_injection_attempt '2024-01-01 | cat'
    [ "$status" -eq 0 ]
}

@test "detect_injection_attempt: AND operator detected" {
    run detect_injection_attempt '2024-01-01 && whoami'
    [ "$status" -eq 0 ]
}

@test "detect_injection_attempt: OR operator detected" {
    run detect_injection_attempt '2024-01-01 || whoami'
    [ "$status" -eq 0 ]
}

@test "detect_injection_attempt: redirect detected" {
    run detect_injection_attempt '2024-01-01 > /tmp/evil'
    [ "$status" -eq 0 ]
}

@test "detect_injection_attempt: newline detected" {
    run detect_injection_attempt $'2024-01-01\n/etc/passwd'
    [ "$status" -eq 0 ]
}

@test "detect_injection_attempt: carriage return detected" {
    run detect_injection_attempt $'2024-01-01\r/etc/passwd'
    [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# validate_file_path
# ---------------------------------------------------------------------------

@test "validate_file_path: normal path accepted" {
    run validate_file_path "/home/user/output.csv"
    [ "$status" -eq 0 ]
}

@test "validate_file_path: parent traversal ../ rejected" {
    run validate_file_path "../../../etc/passwd"
    [ "$status" -ne 0 ]
}

@test "validate_file_path: embedded /.. rejected" {
    run validate_file_path "/home/user/../../../etc/passwd"
    [ "$status" -ne 0 ]
}

@test "validate_file_path: relative path without traversal accepted" {
    run validate_file_path "output/jobs.csv"
    [ "$status" -eq 0 ]
}

# ---------------------------------------------------------------------------
# validate_and_sanitize_date (integration)
# ---------------------------------------------------------------------------

@test "validate_and_sanitize_date: valid slurm date passes and echoes clean date" {
    result=$(validate_and_sanitize_date "2024-01-15" "slurm")
    [ "$result" = "2024-01-15" ]
}

@test "validate_and_sanitize_date: injection attempt rejected" {
    run validate_and_sanitize_date '$(whoami)' "slurm"
    [ "$status" -ne 0 ]
}

@test "validate_and_sanitize_date: valid lsf date passes" {
    result=$(validate_and_sanitize_date "2024/01/15" "lsf")
    [ "$result" = "2024/01/15" ]
}

@test "validate_and_sanitize_date: unknown format rejected" {
    run validate_and_sanitize_date "2024-01-15" "unknown"
    [ "$status" -ne 0 ]
}
