#!/usr/bin/env python3
"""
Generate realistic mock user/group data for cluster analysis

Creates synthetic but realistic job data with user and group patterns that
demonstrate the value of user/group level analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Set seed for reproducibility
np.random.seed(42)
random.seed(42)

# Define research groups with realistic characteristics
GROUPS = {
    'physics': {
        'users': 12,
        'job_profile': 'long_parallel',
        'efficiency': 0.75,
        'growth_rate': 0.02,  # 2% monthly growth
        'peak_season': None,  # Steady year-round
        'waste_factor': 0.15,
    },
    'biology': {
        'users': 18,
        'job_profile': 'short_serial',
        'efficiency': 0.65,
        'growth_rate': 0.08,  # 8% monthly growth (fast!)
        'peak_season': [3, 9],  # March, September (grant deadlines)
        'waste_factor': 0.35,
    },
    'chemistry': {
        'users': 10,
        'job_profile': 'medium_mixed',
        'efficiency': 0.55,
        'growth_rate': -0.01,  # Declining slightly
        'peak_season': None,
        'waste_factor': 0.45,
    },
    'engineering': {
        'users': 15,
        'job_profile': 'short_serial',
        'efficiency': 0.40,  # Low efficiency (course workloads)
        'growth_rate': 0.05,
        'peak_season': [4, 11],  # April, November (course projects)
        'waste_factor': 0.55,
    },
    'ml_lab': {
        'users': 8,
        'job_profile': 'gpu_mixed',
        'efficiency': 0.70,
        'growth_rate': 0.10,  # Fast growth (hot area)
        'peak_season': None,
        'waste_factor': 0.25,
    },
    'astronomy': {
        'users': 6,
        'job_profile': 'long_parallel',
        'efficiency': 0.80,  # High efficiency (experts)
        'growth_rate': 0.01,
        'peak_season': None,
        'waste_factor': 0.10,
    },
    'geoscience': {
        'users': 7,
        'job_profile': 'medium_mixed',
        'efficiency': 0.50,
        'growth_rate': 0.03,
        'peak_season': [6, 7, 8],  # Summer field season
        'waste_factor': 0.40,
    },
}

# Job profiles
JOB_PROFILES = {
    'short_serial': {
        'runtime_hours': lambda: np.random.exponential(0.25),  # Mean 15 min
        'cpus': lambda: np.random.choice([1, 2, 4], p=[0.7, 0.2, 0.1]),
        'memory_gb': lambda: np.random.choice([4, 8, 16, 32], p=[0.4, 0.3, 0.2, 0.1]),
        'gpu': False,
    },
    'medium_mixed': {
        'runtime_hours': lambda: np.random.lognormal(1.5, 1.0),  # Mean ~8 hours
        'cpus': lambda: np.random.choice([1, 4, 8, 16], p=[0.3, 0.4, 0.2, 0.1]),
        'memory_gb': lambda: np.random.choice([8, 16, 32, 64], p=[0.3, 0.3, 0.3, 0.1]),
        'gpu': False,
    },
    'long_parallel': {
        'runtime_hours': lambda: np.random.lognormal(3.5, 0.8),  # Mean ~48 hours
        'cpus': lambda: np.random.choice([8, 16, 32, 64], p=[0.2, 0.3, 0.3, 0.2]),
        'memory_gb': lambda: np.random.choice([32, 64, 128, 256], p=[0.3, 0.4, 0.2, 0.1]),
        'gpu': False,
    },
    'gpu_mixed': {
        'runtime_hours': lambda: np.random.lognormal(0.8, 1.2),  # Mean ~4 hours
        'cpus': lambda: np.random.choice([4, 8, 16], p=[0.5, 0.3, 0.2]),
        'memory_gb': lambda: np.random.choice([32, 64, 128], p=[0.5, 0.3, 0.2]),
        'gpu': True,
    },
}

def generate_users():
    """Generate user list with characteristics"""
    users = []
    user_id = 1

    for group, info in GROUPS.items():
        for i in range(info['users']):
            # Some users are "power users" (top 20%)
            is_power_user = i < info['users'] * 0.2

            # Some users are wasteful (bottom 20% efficiency)
            is_wasteful = i >= info['users'] * 0.8

            users.append({
                'user_id': f"user_{user_id:04d}",
                'username': f"{group}_user{i+1:02d}",
                'group': group,
                'is_power_user': is_power_user,
                'is_wasteful': is_wasteful,
                'job_frequency': 1000 if is_power_user else 200,  # Jobs per year
                'efficiency_modifier': 0.5 if is_wasteful else 1.0,
            })
            user_id += 1

    return pd.DataFrame(users)

def generate_jobs(users_df, start_date, end_date, target_jobs=50000):
    """Generate realistic job data"""

    jobs = []
    current_date = start_date

    total_days = (end_date - start_date).days
    jobs_per_day = target_jobs / total_days

    print(f"Generating ~{target_jobs:,} jobs over {total_days} days...")

    job_id = 1

    while current_date < end_date:
        # Determine jobs for this day
        base_jobs = int(jobs_per_day * np.random.uniform(0.8, 1.2))

        # Adjust for day of week (less on weekends)
        if current_date.weekday() >= 5:  # Weekend
            base_jobs = int(base_jobs * 0.4)

        # Generate jobs for this day
        for _ in range(base_jobs):
            # Select random user
            user = users_df.sample(1).iloc[0]
            group_info = GROUPS[user['group']]

            # Adjust for seasonal peaks
            seasonal_multiplier = 1.0
            if group_info['peak_season']:
                if current_date.month in group_info['peak_season']:
                    seasonal_multiplier = 2.5

            # Skip some jobs if not in peak and not frequent user
            if random.random() > (user['job_frequency'] / 2000) * seasonal_multiplier:
                continue

            # Get job profile
            profile = JOB_PROFILES[group_info['job_profile']]

            # Generate job characteristics
            runtime_hours = min(max(profile['runtime_hours'](), 0.01), 168)  # Cap at 1 week
            cpus_needed = profile['cpus']()
            memory_needed_gb = profile['memory_gb']()

            # Apply waste factor (over-request resources)
            waste_mult = 1.0 + (group_info['waste_factor'] / user['efficiency_modifier'])
            if user['is_wasteful']:
                waste_mult *= 1.5

            cpus_requested = int(cpus_needed * waste_mult)
            memory_requested_gb = int(memory_needed_gb * waste_mult)

            # Some wasteful users request MAX_INT memory
            if user['is_wasteful'] and random.random() < 0.3:
                memory_requested_gb = 9999  # Flag for MAX_INT

            # Submit time (random during business hours for most)
            if random.random() < 0.8:  # 80% during business hours
                submit_hour = random.randint(8, 17)
            else:
                submit_hour = random.randint(0, 23)

            submit_time = current_date + timedelta(hours=submit_hour, minutes=random.randint(0, 59))

            # Queue time (depends on cluster load and job size)
            if cpus_requested <= 4:
                queue_minutes = np.random.exponential(2)  # Small jobs start fast
            else:
                queue_minutes = np.random.exponential(5)

            start_time = submit_time + timedelta(minutes=queue_minutes)
            end_time = start_time + timedelta(hours=runtime_hours)

            # Determine if GPU job
            node_type = 'gpu' if profile['gpu'] else 'compute'

            jobs.append({
                'job_id': job_id,
                'user': user['username'],
                'user_id': user['user_id'],
                'group': user['group'],
                'cpus_req': cpus_requested,
                'cpus_actual': cpus_needed,  # What was actually used
                'mem_req_gb': memory_requested_gb,
                'mem_actual_gb': memory_needed_gb,  # What was actually used
                'runtime_hours': runtime_hours,
                'submit_time': submit_time,
                'start_time': start_time,
                'end_time': end_time,
                'node_type': node_type,
            })

            job_id += 1

        current_date += timedelta(days=1)

        if len(jobs) % 5000 == 0:
            print(f"Generated {len(jobs):,} jobs...")

    return pd.DataFrame(jobs)

def add_derived_metrics(jobs_df):
    """Add efficiency and cost metrics"""

    jobs_df['cpu_efficiency'] = jobs_df['cpus_actual'] / jobs_df['cpus_req']
    jobs_df['mem_efficiency'] = jobs_df['mem_actual_gb'] / jobs_df.apply(
        lambda x: 256 if x['mem_req_gb'] == 9999 else x['mem_req_gb'], axis=1
    )

    # Cost calculation (simplified)
    # $0.10/CPU-hour on-prem, $0.02/CPU-hour cloud
    jobs_df['cost_onprem'] = jobs_df['cpus_req'] * jobs_df['runtime_hours'] * 0.10
    jobs_df['cost_cloud'] = jobs_df['cpus_req'] * jobs_df['runtime_hours'] * 0.02
    jobs_df['cost_waste'] = (jobs_df['cpus_req'] - jobs_df['cpus_actual']) * jobs_df['runtime_hours'] * 0.10

    return jobs_df

def main():
    print("=" * 80)
    print("GENERATING MOCK USER/GROUP DATA")
    print("=" * 80)

    # Generate users
    print("\nGenerating users...")
    users_df = generate_users()
    print(f"Created {len(users_df)} users across {len(GROUPS)} groups")

    # Generate jobs
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)

    jobs_df = generate_jobs(users_df, start_date, end_date, target_jobs=50000)
    print(f"\nGenerated {len(jobs_df):,} total jobs")

    # Add metrics
    print("\nCalculating efficiency and cost metrics...")
    jobs_df = add_derived_metrics(jobs_df)

    # Save data
    print("\nSaving data...")
    users_df.to_csv('mock_users.csv', index=False)
    jobs_df.to_csv('mock_jobs_with_users.csv', index=False)

    print(f"\nFiles created:")
    print(f"  - mock_users.csv ({len(users_df)} users)")
    print(f"  - mock_jobs_with_users.csv ({len(jobs_df):,} jobs)")

    # Quick summary
    print("\n" + "=" * 80)
    print("DATA SUMMARY")
    print("=" * 80)

    print(f"\nJobs by group:")
    for group in jobs_df['group'].value_counts().index:
        count = len(jobs_df[jobs_df['group'] == group])
        total_cost = jobs_df[jobs_df['group'] == group]['cost_onprem'].sum()
        print(f"  {group:15s}: {count:6,} jobs (${total_cost:>12,.0f})")

    print(f"\nTop 10 users by job count:")
    top_users = jobs_df['user'].value_counts().head(10)
    for user, count in top_users.items():
        user_jobs = jobs_df[jobs_df['user'] == user]
        cost = user_jobs['cost_onprem'].sum()
        efficiency = user_jobs['cpu_efficiency'].mean() * 100
        print(f"  {user:20s}: {count:5,} jobs, ${cost:>10,.0f}, {efficiency:>5.1f}% efficient")

    print("\n" + "=" * 80)
    print("Mock data generation complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()
