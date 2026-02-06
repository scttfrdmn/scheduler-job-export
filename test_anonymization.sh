#!/bin/bash
#
# Test Anonymization Workflow
#
# This script demonstrates the complete anonymization process:
# 1. Generate sample data with user information
# 2. Anonymize the data
# 3. Show before/after comparison
# 4. Verify the mapping
#

set -e

echo "========================================================================"
echo "CLUSTER DATA ANONYMIZATION TEST"
echo "========================================================================"
echo ""

# Clean up any previous test files
rm -f sample_jobs_with_users.csv sample_jobs_anon.csv mapping_test.txt

# Step 1: Generate sample data
echo "Step 1: Generating sample data with user information..."
./generate_sample_data_with_users.sh sample_jobs_with_users.csv 100
echo ""

# Step 2: Show original data
echo "========================================================================"
echo "ORIGINAL DATA (with real user/group names):"
echo "========================================================================"
head -n 11 sample_jobs_with_users.csv
echo "..."
echo ""

# Step 3: Anonymize
echo "========================================================================"
echo "Step 2: Running anonymization..."
echo "========================================================================"
./anonymize_cluster_data.sh sample_jobs_with_users.csv sample_jobs_anon.csv mapping_test.txt
echo ""

# Step 4: Show anonymized data
echo "========================================================================"
echo "ANONYMIZED DATA (user/group identities protected):"
echo "========================================================================"
head -n 11 sample_jobs_anon.csv
echo "..."
echo ""

# Step 5: Show mapping (normally this would be secured!)
echo "========================================================================"
echo "MAPPING FILE (ADMIN ONLY - DO NOT SHARE):"
echo "========================================================================"
cat mapping_test.txt
echo ""

# Step 6: Demonstrate analysis on anonymized data
echo "========================================================================"
echo "Example Analysis: Top 5 Users by Job Count (Anonymous IDs)"
echo "========================================================================"
tail -n +2 sample_jobs_anon.csv | cut -d',' -f1 | sort | uniq -c | sort -rn | head -5
echo ""

echo "========================================================================"
echo "Example Analysis: Top 5 Groups by Job Count (Anonymous IDs)"
echo "========================================================================"
tail -n +2 sample_jobs_anon.csv | cut -d',' -f2 | sort | uniq -c | sort -rn | head -5
echo ""

# Step 7: Verify
echo "========================================================================"
echo "VERIFICATION:"
echo "========================================================================"
original_rows=$(tail -n +2 sample_jobs_with_users.csv | wc -l)
anon_rows=$(tail -n +2 sample_jobs_anon.csv | wc -l)

echo "Original rows: $original_rows"
echo "Anonymized rows: $anon_rows"

if [ "$original_rows" -eq "$anon_rows" ]; then
    echo "✓ Row counts match"
else
    echo "✗ Row counts don't match!"
fi

# Check that original usernames don't appear in anonymized data
if grep -q "jsmith\|mjones\|alee" sample_jobs_anon.csv; then
    echo "✗ Warning: Real usernames still present in anonymized data!"
else
    echo "✓ Real usernames successfully removed"
fi

# Check that anonymous IDs are present
if grep -q "user_" sample_jobs_anon.csv; then
    echo "✓ Anonymous user IDs present"
else
    echo "✗ Warning: Anonymous user IDs not found!"
fi

if grep -q "group_" sample_jobs_anon.csv; then
    echo "✓ Anonymous group IDs present"
else
    echo "✗ Warning: Anonymous group IDs not found!"
fi

echo ""
echo "========================================================================"
echo "TEST COMPLETE"
echo "========================================================================"
echo ""
echo "Files created:"
echo "  - sample_jobs_with_users.csv (original with user info)"
echo "  - sample_jobs_anon.csv (anonymized, safe to share)"
echo "  - mapping_test.txt (secure mapping, admin only)"
echo ""
echo "The anonymized CSV preserves all patterns for analysis while"
echo "protecting user identities."
echo ""
echo "In production:"
echo "  1. Export real SLURM data with user/group info"
echo "  2. Run anonymization script"
echo "  3. SECURE the mapping file (chmod 600, encrypt, etc.)"
echo "  4. Share only the anonymized CSV"
echo ""
