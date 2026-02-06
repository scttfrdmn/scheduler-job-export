#!/usr/bin/env python3
"""
Analyze mock user/group data to demonstrate insights

Shows the full value of user/group level analysis:
- Cost allocation by group
- Power user identification
- Waste attribution
- Efficiency scoring
- Peak demand attribution
- Training ROI opportunities
- Cloud migration strategies per group
"""

import pandas as pd
import numpy as np
from datetime import datetime
import sys

def load_data():
    """Load mock data"""
    users = pd.read_csv('mock_users.csv')
    jobs = pd.read_csv('mock_jobs_with_users.csv')

    # Parse dates
    jobs['submit_time'] = pd.to_datetime(jobs['submit_time'])
    jobs['start_time'] = pd.to_datetime(jobs['start_time'])
    jobs['end_time'] = pd.to_datetime(jobs['end_time'])

    return users, jobs

def print_section(title):
    """Print formatted section header"""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)

def analyze_cost_allocation(jobs):
    """Analyze costs by group"""
    print_section("1. COST ALLOCATION BY RESEARCH GROUP")

    group_stats = jobs.groupby('group').agg({
        'job_id': 'count',
        'cost_onprem': 'sum',
        'cost_cloud': 'sum',
        'cost_waste': 'sum',
        'runtime_hours': 'sum',
        'cpus_req': 'sum',
    }).round(0)

    group_stats.columns = ['Jobs', 'OnPrem_Cost', 'Cloud_Cost', 'Waste_Cost', 'Runtime_Hrs', 'CPU_Hours']
    group_stats['Potential_Savings'] = group_stats['OnPrem_Cost'] - group_stats['Cloud_Cost']
    group_stats['Waste_Pct'] = (group_stats['Waste_Cost'] / group_stats['OnPrem_Cost'] * 100).round(1)

    # Sort by cost
    group_stats = group_stats.sort_values('OnPrem_Cost', ascending=False)

    print(f"\n{'Group':<15s} {'Jobs':<8s} {'On-Prem $':<12s} {'Cloud $':<12s} {'Savings $':<12s} {'Waste %':<10s}")
    print("-" * 80)

    for group, row in group_stats.iterrows():
        print(f"{group:<15s} {int(row['Jobs']):<8,} ${int(row['OnPrem_Cost']):<11,} "
              f"${int(row['Cloud_Cost']):<11,} ${int(row['Potential_Savings']):<11,} {row['Waste_Pct']:<10.1f}%")

    total = group_stats.sum()
    total_waste_pct = (total['Waste_Cost'] / total['OnPrem_Cost'] * 100)

    print("-" * 80)
    print(f"{'TOTAL':<15s} {int(total['Jobs']):<8,} ${int(total['OnPrem_Cost']):<11,} "
          f"${int(total['Cloud_Cost']):<11,} ${int(total['Potential_Savings']):<11,} {total_waste_pct:<10.1f}%")

    print(f"\nKey Insights:")
    print(f"  • Total annual on-prem cost: ${int(total['OnPrem_Cost']):,}")
    print(f"  • Potential cloud savings: ${int(total['Potential_Savings']):,} ({total['Potential_Savings']/total['OnPrem_Cost']*100:.1f}%)")
    print(f"  • Waste from over-requesting: ${int(total['Waste_Cost']):,} ({total_waste_pct:.1f}%)")

    return group_stats

def analyze_power_users(jobs):
    """Identify and analyze power users"""
    print_section("2. POWER USER IDENTIFICATION")

    user_stats = jobs.groupby('user').agg({
        'job_id': 'count',
        'cost_onprem': 'sum',
        'cost_waste': 'sum',
        'cpu_efficiency': 'mean',
        'mem_efficiency': 'mean',
    }).round(2)

    user_stats.columns = ['Jobs', 'Cost', 'Waste', 'CPU_Eff', 'Mem_Eff']
    user_stats['Optimization_Potential'] = user_stats['Waste']
    user_stats['Efficiency_Score'] = ((user_stats['CPU_Eff'] + user_stats['Mem_Eff']) / 2 * 10).round(1)

    # Sort by cost
    user_stats = user_stats.sort_values('Cost', ascending=False)

    print(f"\nTop 20 Users by Cost:")
    print(f"\n{'User':<20s} {'Jobs':<8s} {'Annual $':<12s} {'Waste $':<12s} {'Eff Score':<12s} {'Opt. Potential':<12s}")
    print("-" * 90)

    for i, (user, row) in enumerate(user_stats.head(20).iterrows(), 1):
        print(f"{user:<20s} {int(row['Jobs']):<8,} ${int(row['Cost']):<11,} "
              f"${int(row['Waste']):<11,} {row['Efficiency_Score']:<12.1f}/10 ${int(row['Optimization_Potential']):<11,}")

    print("\n📊 Power User Analysis:")
    top_10_cost = user_stats.head(10)['Cost'].sum()
    top_50_cost = user_stats.head(50)['Cost'].sum()
    total_cost = user_stats['Cost'].sum()

    print(f"  • Top 10 users = {top_10_cost/total_cost*100:.1f}% of total cost (${int(top_10_cost):,})")
    print(f"  • Top 50 users = {top_50_cost/total_cost*100:.1f}% of total cost (${int(top_50_cost):,})")

    # Find worst efficiency users
    print(f"\n⚠️  Lowest Efficiency Users (Top Optimization Targets):")
    worst = user_stats.sort_values('Efficiency_Score').head(10)
    for user, row in worst.iterrows():
        if row['Jobs'] > 50:  # Only users with significant usage
            print(f"  • {user}: Score {row['Efficiency_Score']:.1f}/10, "
                  f"{int(row['Jobs'])} jobs, ${int(row['Cost']):,}/year, "
                  f"optimization potential: ${int(row['Waste']):,}")

    return user_stats

def analyze_waste_attribution(jobs):
    """Identify specific waste patterns"""
    print_section("3. RESOURCE WASTE ATTRIBUTION")

    # Find MAX_INT memory users
    max_int_jobs = jobs[jobs['mem_req_gb'] == 9999]

    print(f"\n🚨 MAX_INT Memory Requesters:")
    max_int_users = max_int_jobs.groupby('user').agg({
        'job_id': 'count',
        'cost_waste': 'sum',
        'mem_actual_gb': 'mean',
    }).round(0)
    max_int_users.columns = ['Jobs', 'Waste_Cost', 'Avg_Actual_Mem_GB']
    max_int_users = max_int_users.sort_values('Waste_Cost', ascending=False)

    print(f"\n{'User':<20s} {'Jobs':<8s} {'Waste $':<12s} {'Actual Mem (GB)':<15s} {'Solution':<30s}")
    print("-" * 90)

    for user, row in max_int_users.head(10).iterrows():
        if row['Jobs'] > 10:
            solution = f"Set --mem={int(row['Avg_Actual_Mem_GB'])*2}G"
            print(f"{user:<20s} {int(row['Jobs']):<8,} ${int(row['Waste_Cost']):<11,} "
                  f"{int(row['Avg_Actual_Mem_GB']):<15,} {solution:<30s}")

    # CPU over-requesting
    print(f"\n⚙️  CPU Over-Requesters:")
    jobs['cpu_over_request'] = jobs['cpus_req'] - jobs['cpus_actual']
    cpu_waste = jobs[jobs['cpu_over_request'] > 0].groupby('user').agg({
        'cpu_over_request': 'mean',
        'job_id': 'count',
        'cost_waste': 'sum',
    }).round(1)

    cpu_waste.columns = ['Avg_Wasted_CPUs', 'Jobs', 'Waste_Cost']
    cpu_waste = cpu_waste[cpu_waste['Jobs'] > 50].sort_values('Waste_Cost', ascending=False)

    print(f"\n{'User':<20s} {'Jobs':<8s} {'Avg Wasted CPUs':<18s} {'Waste $':<12s}")
    print("-" * 65)

    for user, row in cpu_waste.head(10).iterrows():
        print(f"{user:<20s} {int(row['Jobs']):<8,} {row['Avg_Wasted_CPUs']:<18.1f} ${int(row['Waste_Cost']):<11,}")

    print(f"\n💡 Quick Wins:")
    print(f"  • {len(max_int_users)} users requesting MAX_INT memory")
    print(f"  • Estimated waste: ${int(max_int_users['Waste_Cost'].sum()):,}/year")
    print(f"  • Solution: 5-minute email or template change")

def analyze_group_efficiency(jobs):
    """Compare efficiency across groups"""
    print_section("4. GROUP EFFICIENCY COMPARISON")

    group_eff = jobs.groupby('group').agg({
        'cpu_efficiency': 'mean',
        'mem_efficiency': 'mean',
        'cost_onprem': 'sum',
        'cost_waste': 'sum',
        'job_id': 'count',
    }).round(3)

    group_eff['Overall_Efficiency'] = ((group_eff['cpu_efficiency'] + group_eff['mem_efficiency']) / 2 * 100).round(1)
    group_eff['Waste_Pct'] = (group_eff['cost_waste'] / group_eff['cost_onprem'] * 100).round(1)

    group_eff = group_eff.sort_values('Overall_Efficiency', ascending=False)

    print(f"\n{'Group':<15s} {'Jobs':<8s} {'CPU Eff %':<12s} {'Mem Eff %':<12s} {'Overall %':<12s} {'Waste %':<10s} {'Annual $':<12s}")
    print("-" * 90)

    for group, row in group_eff.iterrows():
        print(f"{group:<15s} {int(row['job_id']):<8,} {row['cpu_efficiency']*100:<12.1f} "
              f"{row['mem_efficiency']*100:<12.1f} {row['Overall_Efficiency']:<12.1f} "
              f"{row['Waste_Pct']:<10.1f} ${int(row['cost_onprem']):<11,}")

    print(f"\n📈 Efficiency Insights:")
    best_group = group_eff.index[0]
    worst_group = group_eff.index[-1]
    print(f"  • Best: {best_group} ({group_eff.loc[best_group, 'Overall_Efficiency']:.1f}% efficiency)")
    print(f"  • Worst: {worst_group} ({group_eff.loc[worst_group, 'Overall_Efficiency']:.1f}% efficiency)")
    print(f"  • Opportunity: Train {worst_group} using {best_group}'s best practices")

def analyze_peak_attribution(jobs):
    """Identify who drives peak demand"""
    print_section("5. PEAK DEMAND ATTRIBUTION")

    # Sample concurrent load at hourly intervals
    jobs['runtime_seconds'] = (jobs['end_time'] - jobs['start_time']).dt.total_seconds()

    # Find peak time
    start_date = jobs['start_time'].min()
    end_date = jobs['end_time'].max()

    # Sample every 6 hours for performance
    from datetime import timedelta

    sample_times = []
    current = start_date
    while current < end_date:
        sample_times.append(current)
        current += timedelta(hours=6)

    peak_load = 0
    peak_time = None
    peak_jobs = None

    print(f"\nScanning {len(sample_times):,} time points to find peaks...")

    for t in sample_times:
        running = jobs[(jobs['start_time'] <= t) & (jobs['end_time'] > t)]
        load = running['cpus_req'].sum()
        if load > peak_load:
            peak_load = load
            peak_time = t
            peak_jobs = running

    print(f"\nPeak Load Event:")
    print(f"  • Time: {peak_time}")
    print(f"  • Concurrent CPUs: {peak_load:,}")
    print(f"  • Concurrent Jobs: {len(peak_jobs):,}")

    print(f"\nPeak demand by group:")
    peak_by_group = peak_jobs.groupby('group').agg({
        'cpus_req': 'sum',
        'job_id': 'count',
    })
    peak_by_group.columns = ['CPUs', 'Jobs']
    peak_by_group['Pct'] = (peak_by_group['CPUs'] / peak_load * 100).round(1)
    peak_by_group = peak_by_group.sort_values('CPUs', ascending=False)

    print(f"\n{'Group':<15s} {'CPUs':<10s} {'% of Peak':<12s} {'Jobs':<10s}")
    print("-" * 50)

    for group, row in peak_by_group.iterrows():
        print(f"{group:<15s} {int(row['CPUs']):<10,} {row['Pct']:<12.1f}% {int(row['Jobs']):<10,}")

    # Find typical usage for comparison
    print(f"\n📊 Peak vs Typical Usage:")
    for group in peak_by_group.index[:3]:
        peak_cpus = peak_by_group.loc[group, 'CPUs']
        typical = jobs[jobs['group'] == group]['cpus_req'].mean() * len(jobs[jobs['group'] == group]) / 365 / 4
        spike = peak_cpus / typical if typical > 0 else 0
        print(f"  • {group}: {int(peak_cpus):,} CPUs at peak vs {int(typical):,} typical ({spike:.1f}x spike)")

def analyze_cloud_strategy(jobs, group_stats):
    """Recommend cloud strategy per group"""
    print_section("6. GROUP-SPECIFIC CLOUD MIGRATION STRATEGY")

    # Analyze job characteristics per group
    cloud_fit = jobs.groupby('group').apply(lambda x: pd.Series({
        'pct_short': (len(x[x['runtime_hours'] < 1]) / len(x) * 100),
        'pct_long': (len(x[x['runtime_hours'] > 24]) / len(x) * 100),
        'pct_small': (len(x[x['cpus_req'] <= 4]) / len(x) * 100),
        'pct_large': (len(x[x['cpus_req'] > 16]) / len(x) * 100),
        'avg_runtime': x['runtime_hours'].mean(),
        'jobs': len(x),
    })).round(1)

    print(f"\n{'Group':<15s} {'<1hr %':<10s} {'>24hr %':<10s} {'≤4CPU %':<10s} {'Strategy':<40s}")
    print("-" * 90)

    for group, row in cloud_fit.iterrows():
        # Determine strategy
        if row['pct_short'] > 80 and row['pct_small'] > 80:
            strategy = "✅ SPOT INSTANCES (Perfect fit)"
            savings = group_stats.loc[group, 'OnPrem_Cost'] * 0.80  # 80% savings
        elif row['pct_short'] > 60:
            strategy = "✅ MIXED (70% spot, 30% on-demand)"
            savings = group_stats.loc[group, 'OnPrem_Cost'] * 0.60
        elif row['pct_long'] > 50:
            strategy = "⚠️  KEEP ON-PREM (Long jobs, poor cloud fit)"
            savings = group_stats.loc[group, 'OnPrem_Cost'] * 0.10
        else:
            strategy = "✅ BURST (On-prem baseline, cloud peaks)"
            savings = group_stats.loc[group, 'OnPrem_Cost'] * 0.50

        print(f"{group:<15s} {row['pct_short']:<10.0f} {row['pct_long']:<10.0f} "
              f"{row['pct_small']:<10.0f} {strategy:<40s}")
        print(f"{'':15s} Estimated savings: ${int(savings):,}/year")

    print(f"\n💡 Migration Recommendations:")
    print(f"  • Phase 1: Migrate groups with >80% short jobs (lowest risk)")
    print(f"  • Phase 2: Implement bursting for mixed workloads")
    print(f"  • Phase 3: Keep long-running parallel jobs on-prem")

def analyze_growth_trends(jobs):
    """Analyze growth trends by group"""
    print_section("7. GROWTH TRENDS & CAPACITY PLANNING")

    jobs['month'] = jobs['submit_time'].dt.to_period('M')

    monthly = jobs.groupby(['group', 'month']).agg({
        'job_id': 'count',
        'cpus_req': 'sum',
        'cost_onprem': 'sum',
    }).reset_index()

    print(f"\nMonthly job growth by group:")

    for group in monthly['group'].unique():
        group_data = monthly[monthly['group'] == group].sort_values('month')

        if len(group_data) >= 3:
            first_month = group_data.iloc[0]
            last_month = group_data.iloc[-1]

            growth = ((last_month['job_id'] - first_month['job_id']) / first_month['job_id'] * 100)
            cost_growth = ((last_month['cost_onprem'] - first_month['cost_onprem']) / first_month['cost_onprem'] * 100)

            trend = "📈 GROWING" if growth > 10 else "📉 DECLINING" if growth < -10 else "→ STABLE"

            print(f"\n{group:15s} {trend}")
            print(f"  • Job count: {int(first_month['job_id']):,} → {int(last_month['job_id']):,} ({growth:+.1f}%)")
            print(f"  • Monthly cost: ${int(first_month['cost_onprem']):,} → ${int(last_month['cost_onprem']):,} ({cost_growth:+.1f}%)")

            if abs(growth) > 20:
                if growth > 0:
                    print(f"  ⚠️  Action: Increase burst quota by {abs(growth):.0f}% to accommodate growth")
                else:
                    print(f"  💡 Action: Consider reallocating resources to growing groups")

def generate_recommendations(jobs, user_stats, group_stats):
    """Generate actionable recommendations"""
    print_section("8. ACTIONABLE RECOMMENDATIONS")

    total_cost = group_stats['OnPrem_Cost'].sum()
    total_waste = group_stats['Waste_Cost'].sum()
    cloud_savings = group_stats['Potential_Savings'].sum()

    print(f"\n💰 FINANCIAL SUMMARY:")
    print(f"  • Current annual cost: ${int(total_cost):,}")
    print(f"  • Waste from inefficiency: ${int(total_waste):,} ({total_waste/total_cost*100:.1f}%)")
    print(f"  • Cloud migration potential: ${int(cloud_savings):,} ({cloud_savings/total_cost*100:.1f}%)")
    print(f"  • Total opportunity: ${int(total_waste + cloud_savings):,} ({(total_waste + cloud_savings)/total_cost*100:.1f}%)")

    print(f"\n🎯 IMMEDIATE ACTIONS (Month 1-3):")
    print(f"\n1. Power User Optimization ($100-200K potential)")
    top_10_waste = user_stats.sort_values('Waste', ascending=False).head(10)
    print(f"   • Schedule 1-on-1 consultations with top 10 users")
    print(f"   • Combined waste: ${int(top_10_waste['Waste'].sum()):,}/year")
    print(f"   • Effort: 10 hours total")

    max_int_users = len(jobs[jobs['mem_req_gb'] == 9999]['user'].unique())
    print(f"\n2. Fix MAX_INT Memory Requests ($50-100K potential)")
    print(f"   • {max_int_users} users requesting unlimited memory")
    print(f"   • Send template email with proper --mem settings")
    print(f"   • Effort: 2 hours")

    print(f"\n3. Group Efficiency Training ($150-300K potential)")
    worst_groups = group_stats.sort_values('Waste_Pct', ascending=False).head(3)
    print(f"   • Target groups: {', '.join(worst_groups.index)}")
    print(f"   • Combined waste: ${int(worst_groups['Waste_Cost'].sum()):,}/year")
    print(f"   • Host 2-hour workshop per group")
    print(f"   • Effort: 3 workshops × 4 hours prep = 12 hours")

    print(f"\n🚀 STRATEGIC INITIATIVES (Month 3-12):")

    print(f"\n4. Implement Cloud Bursting ($200-500K potential)")
    print(f"   • Configure SLURM elastic_computing plugin")
    print(f"   • Target: Groups with short, parallel jobs")
    print(f"   • Timeline: 3 months")

    print(f"\n5. Chargeback Implementation")
    print(f"   • Monthly cost reports to all PIs")
    print(f"   • Real-time dashboards")
    print(f"   • Behavioral change through visibility")
    print(f"   • Timeline: 2 months")

    print(f"\n6. Fair-Share Optimization")
    print(f"   • Reallocate from under-users to heavy users")
    print(f"   • Quarterly rebalancing")
    print(f"   • Reduce queue times, improve satisfaction")
    print(f"   • Timeline: 1 month")

    print(f"\n📊 EXPECTED ROI:")
    print(f"   • Investment: ~$50K (staff time + training)")
    print(f"   • Year 1 savings: $450-700K")
    print(f"   • ROI: 9-14x")
    print(f"   • Payback: 1 month")

def main():
    print("=" * 80)
    print("MOCK USER/GROUP ANALYSIS EXAMPLE")
    print("=" * 80)
    print("\nThis analysis demonstrates the insights available with user/group data.")
    print("All data is synthetic but representative of real HPC cluster patterns.")

    # Load data
    print("\nLoading mock data...")
    users, jobs = load_data()

    print(f"Loaded {len(users)} users and {len(jobs):,} jobs")

    # Run analyses
    group_stats = analyze_cost_allocation(jobs)
    user_stats = analyze_power_users(jobs)
    analyze_waste_attribution(jobs)
    analyze_group_efficiency(jobs)
    analyze_peak_attribution(jobs)
    analyze_cloud_strategy(jobs, group_stats)
    analyze_growth_trends(jobs)
    generate_recommendations(jobs, user_stats, group_stats)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

    print(f"\n💡 Next Steps:")
    print(f"   1. Export real SLURM data with user/group fields")
    print(f"   2. Use anonymization scripts for privacy")
    print(f"   3. Run this analysis on real data")
    print(f"   4. Identify quick wins and start optimizing!")

if __name__ == "__main__":
    main()
