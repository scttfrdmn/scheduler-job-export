# Cluster Data Anonymization Guide

## Purpose

The anonymization script allows HPC administrators to share job data for analysis while protecting user privacy. It creates consistent anonymous IDs that preserve usage patterns without revealing actual identities.

## Why Anonymize?

**Benefits:**
- ✅ Enable external analysis and consulting
- ✅ Share data for research without privacy concerns
- ✅ Preserve per-user and per-group patterns for analysis
- ✅ Consistent mapping (same user = same ID across dataset)
- ✅ Comply with privacy policies and regulations

**What's Preserved:**
- Per-user resource usage patterns
- Per-group resource usage patterns
- Temporal patterns
- Job characteristics (CPUs, memory, runtime, etc.)
- All relationships between jobs and users/groups

**What's Protected:**
- User identities
- Group/department names
- Any personally identifiable information

## Quick Start

### 1. Export Job Data with User Information

First, export your SLURM data **with user/group columns**:

```bash
# Example SLURM sacct export with user information
sacct -a \
  --format=User,Group,Account,CPUs,ReqMem,NNodes,NodeList,AllocTRES,Start,End,Submit \
  --starttime 2024-01-01 \
  --endtime 2025-01-01 \
  --parsable2 \
  > jobs_with_users.csv
```

Expected columns (any combination):
- **User identification:** `user`, `uid`, `username`, `account`
- **Group identification:** `group`, `gid`, `groupname`
- **Plus your other job data:** CPU, memory, time, etc.

### 2. Run Anonymization

```bash
chmod +x anonymize_cluster_data.sh
./anonymize_cluster_data.sh jobs_with_users.csv jobs_anonymized.csv mapping.txt
```

### 3. Secure the Mapping File

```bash
# Set restrictive permissions
chmod 600 mapping.txt

# Move to secure location
sudo mv mapping.txt /root/secure/cluster_mapping_2024.txt

# Or encrypt it
gpg -c mapping.txt
shred -u mapping.txt  # Securely delete original
```

### 4. Share Anonymized Data

The `jobs_anonymized.csv` file can now be safely shared for analysis!

## Example

### Input Data (jobs_with_users.csv)
```csv
user,group,cpus_req,mem_req,nodes_alloc,submit_time
jsmith,physics,4,16384,1,2024-09-30 14:30:00
mjones,biology,1,8192,1,2024-09-30 14:31:00
jsmith,physics,8,32768,1,2024-09-30 15:00:00
alee,chemistry,2,16384,1,2024-09-30 15:15:00
mjones,biology,1,8192,1,2024-09-30 15:30:00
```

### Output Data (jobs_anonymized.csv)
```csv
user,group,cpus_req,mem_req,nodes_alloc,submit_time
user_0001,group_A,4,16384,1,2024-09-30 14:30:00
user_0002,group_B,1,8192,1,2024-09-30 14:31:00
user_0001,group_A,8,32768,1,2024-09-30 15:00:00
user_0003,group_C,2,16384,1,2024-09-30 15:15:00
user_0002,group_B,1,8192,1,2024-09-30 15:30:00
```

### Mapping File (mapping.txt)
```
================================================================================
CLUSTER DATA ANONYMIZATION MAPPING
================================================================================
CONFIDENTIAL - ADMIN ACCESS ONLY
================================================================================

USER MAPPINGS:
--------------------------------------------------------------------------------
user_0001       -> jsmith
user_0002       -> mjones
user_0003       -> alee

GROUP MAPPINGS:
--------------------------------------------------------------------------------
group_A         -> physics
group_B         -> biology
group_C         -> chemistry

================================================================================
Total users anonymized: 3
Total groups anonymized: 3
================================================================================
```

## What the Script Does

1. **Detects columns** - Automatically finds user/group columns
2. **Extracts unique values** - Identifies all distinct users and groups
3. **Creates consistent mappings:**
   - Users: `user_0001`, `user_0002`, etc.
   - Groups: `group_A`, `group_B`, etc.
4. **Preserves patterns** - Same user always gets same anonymous ID
5. **Outputs:**
   - Anonymized CSV for sharing
   - Secure mapping file for admin reference

## Security Best Practices

### For the Mapping File

⚠️ **CRITICAL:** The mapping file allows de-anonymization!

**Required:**
- ✅ `chmod 600` - Restrict to owner only
- ✅ Store in secure admin-only location
- ✅ Consider encryption (`gpg -c mapping.txt`)
- ✅ Include date in filename for tracking
- ✅ Backup securely

**Never:**
- ❌ Share mapping file with anonymized data
- ❌ Store in world-readable location
- ❌ Email or transfer over insecure channels
- ❌ Include in git repositories

### For the Anonymized Data

✅ **Safe to share:**
- With external consultants
- For research publications
- In public repositories (if appropriate)
- With collaborators

⚠️ **Still be cautious:**
- Very rare usage patterns might be identifiable
- Combination with other data sources could reveal identities
- Consider aggregating very small groups
- Review before publishing

## Advanced Usage

### Custom Column Names

The script auto-detects these column names (case-insensitive):
- **Users:** `user`, `uid`, `username`, `account`
- **Groups:** `group`, `gid`, `groupname`

If your columns have different names, rename them first:

```bash
# Example: rename columns in CSV
sed '1s/owner/user/' jobs.csv > jobs_renamed.csv
```

### Handling Large Files

For very large files (>1GB):

```bash
# Process in chunks
split -l 1000000 jobs_with_users.csv chunk_

# Anonymize each chunk
for chunk in chunk_*; do
  ./anonymize_cluster_data.sh "$chunk" "anon_$chunk" mapping.txt
done

# Combine (keeping only one header)
head -n 1 anon_chunk_aa > jobs_anonymized.csv
tail -n +2 -q anon_chunk_* >> jobs_anonymized.csv
```

### Encrypting Mapping File

```bash
# Encrypt with GPG
gpg -c mapping.txt
# Creates: mapping.txt.gpg

# Securely delete original
shred -u mapping.txt

# Later, decrypt when needed
gpg -d mapping.txt.gpg > mapping.txt
```

### Multiple Datasets

For consistency across multiple exports, reuse the same mapping:

```bash
# First export
./anonymize_cluster_data.sh jobs_2024.csv anon_2024.csv mapping_2024.txt

# Later export - manually apply same mapping
# (Would need to extract mappings and reapply)
```

## What Can Be Analyzed with Anonymized Data

### Possible Analyses:
- ✅ Per-user resource utilization
- ✅ Per-group resource utilization
- ✅ User behavior patterns
- ✅ Power user identification (as anonymous IDs)
- ✅ Fairshare and allocation analysis
- ✅ Usage by department (anonymized)
- ✅ Inefficient user patterns
- ✅ All temporal and resource patterns

### Example Analysis:

```python
import pandas as pd

df = pd.read_csv('jobs_anonymized.csv')

# Analyze top users (anonymously)
user_stats = df.groupby('user').agg({
    'cpus_req': 'sum',
    'job_id': 'count'
}).sort_values('cpus_req', ascending=False)

print("Top 10 users by CPU consumption:")
print(user_stats.head(10))

# Output shows anonymous IDs:
# user_0042: 45,234 CPU-hours
# user_0107: 38,901 CPU-hours
# etc.
```

## Validation

After anonymization, verify:

```bash
# Check row counts match
echo "Input rows: $(tail -n +2 jobs_with_users.csv | wc -l)"
echo "Output rows: $(tail -n +2 jobs_anonymized.csv | wc -l)"

# Check no real usernames remain
grep -i "jsmith\|mjones" jobs_anonymized.csv
# Should return nothing

# Check anonymous IDs are present
head jobs_anonymized.csv
# Should show user_0001, group_A, etc.

# Verify mapping file is secure
ls -la mapping.txt
# Should show: -rw------- (600 permissions)
```

## Troubleshooting

### Script doesn't detect user/group columns

**Problem:** Your columns have non-standard names

**Solution:** Rename columns before anonymizing:
```bash
# Example: your CSV has "owner" instead of "user"
sed '1s/owner/user/;1s/dept/group/' original.csv > prepared.csv
./anonymize_cluster_data.sh prepared.csv anonymized.csv
```

### Large file takes too long

**Problem:** File is very large (>2GB)

**Solution:** Use the chunking approach (see Advanced Usage above)

### Need to de-anonymize specific user

**Problem:** You need to identify a specific user for follow-up

**Solution:**
```bash
# Search mapping file securely
grep "user_0042" /root/secure/mapping.txt
# Shows: user_0042 -> actual_username
```

## Integration with SLURM

### Full Pipeline

```bash
#!/bin/bash
# export_and_anonymize.sh

EXPORT_FILE="jobs_$(date +%Y%m%d).csv"
ANON_FILE="jobs_$(date +%Y%m%d)_anon.csv"
MAPPING_FILE="/root/secure/mapping_$(date +%Y%m%d).txt"

# Export from SLURM with user info
sacct -a \
  --format=User,Group,Account,JobID,JobName,Partition,CPUs,ReqMem,NNodes,NodeList,AllocTRES,Start,End,Submit,State \
  --starttime $(date -d '1 year ago' +%Y-%m-%d) \
  --endtime $(date +%Y-%m-%d) \
  --parsable2 \
  > "$EXPORT_FILE"

# Anonymize
./anonymize_cluster_data.sh "$EXPORT_FILE" "$ANON_FILE" "$MAPPING_FILE"

# Secure mapping file
chmod 600 "$MAPPING_FILE"

# The anonymized file can now be shared
echo "Anonymized data ready: $ANON_FILE"
echo "Mapping secured at: $MAPPING_FILE"
```

## Legal and Compliance

### GDPR Compliance

Anonymization helps with GDPR compliance by:
- Removing personally identifiable information (PII)
- Preventing direct identification of individuals
- Allowing "research and statistics" exemptions

**Note:** Consult your legal team for specific requirements.

### Data Retention

- Keep mapping files for audit purposes
- Document anonymization process
- Include date and version in filenames
- Maintain chain of custody

## Support

For issues or questions:
1. Check this README
2. Review script output and error messages
3. Validate input CSV format
4. Check permissions on output directories

---

**Remember:** The mapping file is the key to de-anonymization. Protect it like you would protect the original data with user information.
