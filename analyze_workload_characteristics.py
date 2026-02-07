#!/usr/bin/env python3
"""
Workload Characterization Analysis

Analyzes:
1. Arrival patterns - Uncorrelated arrivals across groups and system
2. Heavy-tailed jobs - Power-law distributions, frequency, impact
3. Temporal statistics - Burstiness, inter-arrival times, autocorrelation

Statistical tests:
- Poisson arrival testing
- Cross-correlation between groups
- Heavy-tail distribution fitting (Pareto, log-normal)
- Autocorrelation analysis
- Burstiness index

Outputs per-user, per-group, and system-wide statistics.
"""

import pandas as pd
import numpy as np
import sys
from datetime import datetime, timedelta
from scipy import stats
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

def load_job_data(filename):
    """Load job data with timing information"""
    print(f"Loading job data from {filename}...")

    df = pd.read_csv(filename)

    # Parse timestamps
    for col in ['submit_time', 'start_time', 'end_time']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Calculate runtime
    if 'start_time' in df.columns and 'end_time' in df.columns:
        df['runtime_seconds'] = (df['end_time'] - df['start_time']).dt.total_seconds()
        df['runtime_hours'] = df['runtime_seconds'] / 3600
        df = df[df['runtime_seconds'] > 0]  # Remove invalid

    # Parse resources
    if 'cpus' in df.columns:
        df['cpus'] = pd.to_numeric(df['cpus'], errors='coerce').fillna(1)

    # Sort by submit time
    df = df.sort_values('submit_time').reset_index(drop=True)

    print(f"Loaded {len(df):,} jobs")
    print(f"Time range: {df['submit_time'].min()} to {df['submit_time'].max()}")

    return df

def analyze_arrival_patterns(df):
    """Analyze job arrival patterns - test for Poisson arrivals"""
    print("\n" + "="*80)
    print("ARRIVAL PATTERN ANALYSIS")
    print("="*80)

    # Calculate inter-arrival times (seconds)
    df['inter_arrival_seconds'] = df['submit_time'].diff().dt.total_seconds()
    df['inter_arrival_minutes'] = df['inter_arrival_seconds'] / 60

    # Remove first row (no previous arrival)
    inter_arrivals = df['inter_arrival_seconds'].dropna()

    print(f"\nSystem-wide Arrivals:")
    print(f"  Total jobs:                {len(df):,}")
    print(f"  Mean inter-arrival time:   {inter_arrivals.mean():.1f} seconds ({inter_arrivals.mean()/60:.1f} min)")
    print(f"  Median inter-arrival time: {inter_arrivals.median():.1f} seconds ({inter_arrivals.median()/60:.1f} min)")
    print(f"  Std dev inter-arrival:     {inter_arrivals.std():.1f} seconds")
    print(f"  Min inter-arrival:         {inter_arrivals.min():.1f} seconds")
    print(f"  Max inter-arrival:         {inter_arrivals.max():.1f} seconds")

    # Coefficient of Variation (CV)
    cv = inter_arrivals.std() / inter_arrivals.mean()
    print(f"  Coefficient of Variation:  {cv:.3f}")

    # For Poisson process, CV ≈ 1
    if cv < 0.8:
        print(f"    → More regular than Poisson (CV < 1)")
    elif cv > 1.2:
        print(f"    → More bursty than Poisson (CV > 1)")
    else:
        print(f"    → Approximately Poisson (CV ≈ 1)")

    # Test for exponential distribution (Poisson arrivals)
    # Exponential fit
    lambda_param = 1 / inter_arrivals.mean()

    # Kolmogorov-Smirnov test
    ks_stat, ks_pval = stats.kstest(inter_arrivals, 'expon', args=(0, 1/lambda_param))
    print(f"\nExponential Distribution Test (Poisson arrivals):")
    print(f"  KS statistic: {ks_stat:.4f}")
    print(f"  p-value:      {ks_pval:.4f}")

    if ks_pval > 0.05:
        print(f"    → Cannot reject Poisson arrivals (p > 0.05)")
    else:
        print(f"    → Reject Poisson arrivals (p < 0.05) - arrivals are NOT random")

    # Burstiness index: (σ² - μ) / (σ² + μ)
    # -1 = regular, 0 = Poisson, 1 = bursty
    mean_ia = inter_arrivals.mean()
    var_ia = inter_arrivals.var()
    burstiness = (var_ia - mean_ia) / (var_ia + mean_ia)

    print(f"\nBurstiness Index: {burstiness:.3f}")
    if burstiness < -0.1:
        print(f"  → Regular arrivals (negative)")
    elif burstiness > 0.1:
        print(f"  → Bursty arrivals (positive)")
    else:
        print(f"  → Random/Poisson arrivals (≈0)")

    # Hourly arrival rates
    df['submit_hour'] = df['submit_time'].dt.hour
    hourly_counts = df.groupby('submit_hour').size()

    print(f"\nHourly Arrival Rate Variation:")
    print(f"  Min arrivals (hour {hourly_counts.idxmin()}): {hourly_counts.min():,} jobs")
    print(f"  Max arrivals (hour {hourly_counts.idxmax()}): {hourly_counts.max():,} jobs")
    print(f"  Ratio (max/min): {hourly_counts.max() / hourly_counts.min():.1f}x")

    return inter_arrivals, burstiness

def analyze_group_arrival_correlation(df):
    """Analyze cross-correlation of arrivals between groups"""
    print("\n" + "="*80)
    print("GROUP ARRIVAL CORRELATION ANALYSIS")
    print("="*80)

    if 'group' not in df.columns:
        print("  Warning: No 'group' column found")
        return None

    # Create hourly time bins
    df['hour_bin'] = df['submit_time'].dt.floor('H')

    # Count arrivals per hour per group
    group_arrivals = df.groupby(['hour_bin', 'group']).size().unstack(fill_value=0)

    # Get top groups by total jobs
    top_groups = df['group'].value_counts().head(10).index.tolist()
    group_arrivals_top = group_arrivals[top_groups]

    print(f"\nAnalyzing top {len(top_groups)} groups...")

    # Calculate correlation matrix
    corr_matrix = group_arrivals_top.corr()

    print(f"\nCross-correlation between groups (hourly arrivals):")
    print(f"  Mean correlation (off-diagonal): {corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean():.3f}")
    print(f"  Max correlation:  {corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].max():.3f}")
    print(f"  Min correlation:  {corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].min():.3f}")

    # If mean correlation near 0, arrivals are uncorrelated
    mean_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean()

    if abs(mean_corr) < 0.1:
        print(f"    → Groups submit independently (uncorrelated)")
    elif mean_corr > 0.3:
        print(f"    → Groups show positive correlation (coordinated behavior)")
    elif mean_corr < -0.1:
        print(f"    → Groups show negative correlation (avoiding each other)")

    # Find highly correlated group pairs
    print(f"\nHighly correlated group pairs (r > 0.5):")
    found_pairs = False
    for i in range(len(corr_matrix)):
        for j in range(i+1, len(corr_matrix)):
            if corr_matrix.iloc[i, j] > 0.5:
                print(f"  {corr_matrix.index[i]:20s} <-> {corr_matrix.columns[j]:20s}: r = {corr_matrix.iloc[i, j]:.3f}")
                found_pairs = True

    if not found_pairs:
        print(f"  No highly correlated pairs found")

    return corr_matrix

def analyze_heavy_tailed_distribution(df):
    """Analyze heavy-tailed job runtime distribution"""
    print("\n" + "="*80)
    print("HEAVY-TAILED DISTRIBUTION ANALYSIS")
    print("="*80)

    if 'runtime_hours' not in df.columns:
        print("  Warning: No runtime data available")
        return None

    runtimes = df['runtime_hours'].dropna()

    print(f"\nRuntime Statistics:")
    print(f"  Mean:       {runtimes.mean():>10.2f} hours")
    print(f"  Median:     {runtimes.median():>10.2f} hours")
    print(f"  Std dev:    {runtimes.std():>10.2f} hours")
    print(f"  Max:        {runtimes.max():>10.2f} hours ({runtimes.max()/24:.1f} days)")
    print(f"  99th %ile:  {runtimes.quantile(0.99):>10.2f} hours")
    print(f"  95th %ile:  {runtimes.quantile(0.95):>10.2f} hours")

    # Skewness and kurtosis (heavy-tailed indicators)
    skew = stats.skew(runtimes)
    kurt = stats.kurtosis(runtimes)

    print(f"\nDistribution Shape:")
    print(f"  Skewness:   {skew:>10.3f}")
    print(f"  Kurtosis:   {kurt:>10.3f}")

    if skew > 1:
        print(f"    → Highly right-skewed (heavy right tail)")
    if kurt > 3:
        print(f"    → High kurtosis (heavy tails)")

    # Test for log-normal distribution (common in HPC)
    log_runtimes = np.log(runtimes[runtimes > 0])
    shapiro_stat, shapiro_pval = stats.shapiro(log_runtimes[:5000])  # Sample for performance

    print(f"\nLog-normal Distribution Test:")
    print(f"  Shapiro-Wilk p-value: {shapiro_pval:.4f}")

    if shapiro_pval > 0.05:
        print(f"    → Log-normal distribution (typical HPC workload)")
    else:
        print(f"    → Not log-normal")

    # Identify heavy-tailed jobs (> 95th percentile)
    p95 = runtimes.quantile(0.95)
    heavy_tail = df[df['runtime_hours'] > p95].copy()

    print(f"\nHeavy-Tailed Jobs (> 95th percentile = {p95:.2f} hours):")
    print(f"  Count:              {len(heavy_tail):,} ({len(heavy_tail)/len(df)*100:.1f}%)")
    print(f"  Mean runtime:       {heavy_tail['runtime_hours'].mean():.2f} hours")
    print(f"  Total CPU-hours:    {(heavy_tail['runtime_hours'] * heavy_tail['cpus']).sum():,.0f}")

    # % of total CPU-hours consumed by heavy-tailed jobs
    total_cpu_hours = (df['runtime_hours'] * df['cpus']).sum()
    heavy_cpu_hours = (heavy_tail['runtime_hours'] * heavy_tail['cpus']).sum()

    print(f"  % of total CPU-hours: {heavy_cpu_hours / total_cpu_hours * 100:.1f}%")
    print(f"    → Top 5% of jobs consume {heavy_cpu_hours / total_cpu_hours * 100:.1f}% of CPU-hours")

    # Power law exponent estimation (Pareto distribution)
    # α = 1 + n / Σ(log(xi/xmin))
    xmin = runtimes.min()
    alpha = 1 + len(runtimes) / np.sum(np.log(runtimes / xmin))

    print(f"\nPower Law Exponent (Pareto α): {alpha:.3f}")
    if alpha < 2:
        print(f"    → Very heavy tail (α < 2, infinite variance)")
    elif alpha < 3:
        print(f"    → Heavy tail (2 < α < 3, finite variance)")
    else:
        print(f"    → Moderate tail (α > 3)")

    return heavy_tail

def analyze_heavy_tail_by_user_group(df, heavy_tail):
    """Analyze which users/groups submit heavy-tailed jobs"""
    print("\n" + "="*80)
    print("HEAVY-TAILED JOBS BY USER AND GROUP")
    print("="*80)

    # Per-user analysis
    if 'user' in df.columns and 'user' in heavy_tail.columns:
        user_heavy = heavy_tail.groupby('user').agg({
            'runtime_hours': ['count', 'mean', 'sum'],
            'cpus': 'sum'
        }).reset_index()

        user_heavy.columns = ['user', 'heavy_jobs', 'avg_heavy_runtime', 'total_heavy_hours', 'total_cpus']

        # Add total jobs for comparison
        user_total = df.groupby('user').size().reset_index(name='total_jobs')
        user_heavy = user_heavy.merge(user_total, on='user')

        user_heavy['heavy_job_pct'] = user_heavy['heavy_jobs'] / user_heavy['total_jobs'] * 100
        user_heavy['cpu_hours_heavy'] = user_heavy['total_heavy_hours'] * user_heavy['total_cpus']

        user_heavy = user_heavy.sort_values('heavy_jobs', ascending=False)

        print(f"\nTop Users by Heavy-Tailed Job Count:")
        for idx, row in user_heavy.head(10).iterrows():
            print(f"  {row['user']:20s}: {row['heavy_jobs']:>6.0f} heavy jobs "
                  f"({row['heavy_job_pct']:>5.1f}% of their jobs)")

    # Per-group analysis
    if 'group' in df.columns and 'group' in heavy_tail.columns:
        group_heavy = heavy_tail.groupby('group').agg({
            'runtime_hours': ['count', 'mean', 'sum'],
        }).reset_index()

        group_heavy.columns = ['group', 'heavy_jobs', 'avg_heavy_runtime', 'total_heavy_hours']

        # Add total jobs
        group_total = df.groupby('group').size().reset_index(name='total_jobs')
        group_heavy = group_heavy.merge(group_total, on='group')

        group_heavy['heavy_job_pct'] = group_heavy['heavy_jobs'] / group_heavy['total_jobs'] * 100
        group_heavy = group_heavy.sort_values('heavy_jobs', ascending=False)

        print(f"\nTop Groups by Heavy-Tailed Job Count:")
        for idx, row in group_heavy.head(10).iterrows():
            print(f"  {row['group']:20s}: {row['heavy_jobs']:>6.0f} heavy jobs "
                  f"({row['heavy_job_pct']:>5.1f}% of their jobs)")

        return user_heavy, group_heavy

    return None, None

def analyze_temporal_heavy_tail_patterns(df, heavy_tail):
    """Analyze temporal patterns of heavy-tailed jobs"""
    print("\n" + "="*80)
    print("TEMPORAL PATTERNS OF HEAVY-TAILED JOBS")
    print("="*80)

    heavy_tail['submit_hour'] = heavy_tail['submit_time'].dt.hour
    heavy_tail['submit_dayofweek'] = heavy_tail['submit_time'].dt.dayofweek

    # All jobs for comparison
    df['submit_hour'] = df['submit_time'].dt.hour
    df['submit_dayofweek'] = df['submit_time'].dt.dayofweek

    print(f"\nBy Hour of Day:")
    print(f"  Hour  All Jobs  Heavy Jobs  % Heavy")
    for hour in range(0, 24, 3):  # Every 3 hours
        all_count = (df['submit_hour'] == hour).sum()
        heavy_count = (heavy_tail['submit_hour'] == hour).sum()
        pct = heavy_count / all_count * 100 if all_count > 0 else 0
        print(f"  {hour:02d}:00 {all_count:>8,}  {heavy_count:>10,}  {pct:>7.1f}%")

    print(f"\nBy Day of Week:")
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    print(f"  Day   All Jobs  Heavy Jobs  % Heavy")
    for day in range(7):
        all_count = (df['submit_dayofweek'] == day).sum()
        heavy_count = (heavy_tail['submit_dayofweek'] == day).sum()
        pct = heavy_count / all_count * 100 if all_count > 0 else 0
        print(f"  {days[day]:3s}  {all_count:>8,}  {heavy_count:>10,}  {pct:>7.1f}%")

def analyze_autocorrelation(df):
    """Analyze autocorrelation in arrival process"""
    print("\n" + "="*80)
    print("AUTOCORRELATION ANALYSIS")
    print("="*80)

    # Create hourly time series
    df['hour_bin'] = df['submit_time'].dt.floor('H')
    hourly_arrivals = df.groupby('hour_bin').size()

    # Ensure continuous time series
    full_range = pd.date_range(start=hourly_arrivals.index.min(),
                               end=hourly_arrivals.index.max(),
                               freq='H')
    hourly_arrivals = hourly_arrivals.reindex(full_range, fill_value=0)

    # Calculate autocorrelation for lags 1-24 hours
    print(f"\nAutocorrelation of hourly arrivals:")
    print(f"  Lag (hours)  ACF")

    acf_values = []
    lags = [1, 2, 3, 6, 12, 24, 48, 168]  # 1h, 2h, 3h, 6h, 12h, 24h, 48h, 1week

    for lag in lags:
        if lag < len(hourly_arrivals):
            # Calculate autocorrelation
            acf = hourly_arrivals.autocorr(lag=lag)
            acf_values.append(acf)
            print(f"  {lag:>4d}         {acf:>6.3f}")
        else:
            acf_values.append(np.nan)

    # Interpretation
    if acf_values[0] > 0.5:  # 1-hour lag
        print(f"\n  → Strong hourly autocorrelation (clustered arrivals)")

    if len(acf_values) > 5 and acf_values[5] > 0.3:  # 24-hour lag
        print(f"  → Daily pattern detected")

    if len(acf_values) > 7 and acf_values[7] > 0.3:  # 168-hour (weekly) lag
        print(f"  → Weekly pattern detected")

    return acf_values

def save_results(df, inter_arrivals, heavy_tail, user_heavy, group_heavy):
    """Save analysis results"""
    print("\nSaving results...")

    # Inter-arrival times
    inter_arrival_df = pd.DataFrame({
        'inter_arrival_seconds': inter_arrivals,
        'inter_arrival_minutes': inter_arrivals / 60,
        'inter_arrival_hours': inter_arrivals / 3600
    })
    inter_arrival_df.to_csv('arrival_inter_arrival_times.csv', index=False)
    print(f"  Saved arrival_inter_arrival_times.csv")

    # Heavy-tailed jobs
    if heavy_tail is not None:
        heavy_tail_output = heavy_tail[['user', 'group', 'submit_time', 'start_time',
                                        'end_time', 'runtime_hours', 'cpus']].copy()
        heavy_tail_output.to_csv('heavy_tailed_jobs.csv', index=False)
        print(f"  Saved heavy_tailed_jobs.csv ({len(heavy_tail):,} jobs)")

    # User heavy-tail stats
    if user_heavy is not None:
        user_heavy.to_csv('heavy_tail_by_user.csv', index=False)
        print(f"  Saved heavy_tail_by_user.csv")

    # Group heavy-tail stats
    if group_heavy is not None:
        group_heavy.to_csv('heavy_tail_by_group.csv', index=False)
        print(f"  Saved heavy_tail_by_group.csv")

    # Hourly arrival counts (for correlation analysis)
    df['hour_bin'] = df['submit_time'].dt.floor('H')

    if 'group' in df.columns:
        group_hourly = df.groupby(['hour_bin', 'group']).size().unstack(fill_value=0)
        group_hourly.to_csv('arrivals_hourly_by_group.csv')
        print(f"  Saved arrivals_hourly_by_group.csv")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_workload_characteristics.py <jobs_csv>")
        print("")
        print("Analyzes workload characteristics including:")
        print("  - Arrival patterns (Poisson testing, burstiness)")
        print("  - Group arrival correlation (independent vs coordinated)")
        print("  - Heavy-tailed distribution (power law, log-normal)")
        print("  - Temporal patterns of heavy-tailed jobs")
        print("  - Autocorrelation analysis")
        print("")
        print("Required columns:")
        print("  - submit_time, start_time, end_time")
        print("  - user, group (for per-user/group analysis)")
        print("")
        print("Outputs:")
        print("  - arrival_inter_arrival_times.csv - Inter-arrival statistics")
        print("  - heavy_tailed_jobs.csv - Jobs > 95th percentile runtime")
        print("  - heavy_tail_by_user.csv - User heavy-tail statistics")
        print("  - heavy_tail_by_group.csv - Group heavy-tail statistics")
        print("  - arrivals_hourly_by_group.csv - Hourly arrivals for correlation")
        sys.exit(1)

    jobs_file = sys.argv[1]

    # Load data
    df = load_job_data(jobs_file)

    # Analyze arrival patterns
    inter_arrivals, burstiness = analyze_arrival_patterns(df)

    # Analyze group correlation
    corr_matrix = analyze_group_arrival_correlation(df)

    # Analyze heavy-tailed distribution
    heavy_tail = analyze_heavy_tailed_distribution(df)

    # Analyze heavy-tail by user/group
    user_heavy, group_heavy = None, None
    if heavy_tail is not None:
        user_heavy, group_heavy = analyze_heavy_tail_by_user_group(df, heavy_tail)
        analyze_temporal_heavy_tail_patterns(df, heavy_tail)

    # Autocorrelation analysis
    acf_values = analyze_autocorrelation(df)

    # Save results
    save_results(df, inter_arrivals, heavy_tail, user_heavy, group_heavy)

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nKey Findings:")
    print(f"  Burstiness Index: {burstiness:.3f}")

    if corr_matrix is not None:
        mean_corr = corr_matrix.values[np.triu_indices_from(corr_matrix.values, k=1)].mean()
        print(f"  Mean group correlation: {mean_corr:.3f}")

    if heavy_tail is not None:
        total_cpu_hours = (df['runtime_hours'] * df['cpus']).sum()
        heavy_cpu_hours = (heavy_tail['runtime_hours'] * heavy_tail['cpus']).sum()
        print(f"  Heavy-tail impact: Top 5% of jobs = {heavy_cpu_hours / total_cpu_hours * 100:.1f}% of CPU-hours")

    print("\nOutput files:")
    print("  arrival_inter_arrival_times.csv")
    print("  heavy_tailed_jobs.csv")
    print("  heavy_tail_by_user.csv")
    print("  heavy_tail_by_group.csv")
    print("  arrivals_hourly_by_group.csv")
    print("")
    print("Use these files to:")
    print("  - Validate queueing models (Poisson vs bursty)")
    print("  - Identify heavy-tail users for scheduling policies")
    print("  - Understand group coordination patterns")
    print("  - Plan capacity for long-running jobs")
    print("")
    print("="*80)

if __name__ == '__main__':
    main()
