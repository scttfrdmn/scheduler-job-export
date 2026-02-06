#!/usr/bin/env python3
"""
Visualize Utilization Time Series

Creates publication-quality charts from utilization time series data.

Generates:
- CPU utilization over time
- Memory utilization over time
- Combined CPU+Memory chart
- Distribution histograms
- Daily/weekly aggregations
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sys
from datetime import datetime
import numpy as np

def load_timeseries(filename):
    """Load time series data"""
    print(f"Loading time series from {filename}...")

    df = pd.read_csv(filename)

    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"  Loaded {len(df):,} data points")
    print(f"  Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    return df

def plot_cpu_utilization(df, output_file='cpu_utilization_timeline.png'):
    """Plot CPU utilization over time"""
    print(f"\nCreating CPU utilization chart...")

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(df['timestamp'], df['cpu_utilization_pct'],
            linewidth=0.5, alpha=0.7, color='#2E86AB')

    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('CPU Utilization (%)', fontsize=12)
    ax.set_title('CPU Utilization Over Time', fontsize=14, fontweight='bold')

    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, max(105, df['cpu_utilization_pct'].max() * 1.05))

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha='right')

    # Add statistics
    mean_util = df['cpu_utilization_pct'].mean()
    median_util = df['cpu_utilization_pct'].median()
    max_util = df['cpu_utilization_pct'].max()

    ax.axhline(y=mean_util, color='red', linestyle='--', linewidth=1,
               alpha=0.7, label=f'Mean: {mean_util:.1f}%')
    ax.axhline(y=median_util, color='orange', linestyle='--', linewidth=1,
               alpha=0.7, label=f'Median: {median_util:.1f}%')

    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved to {output_file}")

    plt.close()

def plot_memory_utilization(df, output_file='memory_utilization_timeline.png'):
    """Plot memory utilization over time"""
    print(f"\nCreating memory utilization chart...")

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(df['timestamp'], df['memory_utilization_pct'],
            linewidth=0.5, alpha=0.7, color='#A23B72')

    ax.set_xlabel('Time', fontsize=12)
    ax.set_ylabel('Memory Utilization (%)', fontsize=12)
    ax.set_title('Memory Utilization Over Time', fontsize=14, fontweight='bold')

    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, max(105, df['memory_utilization_pct'].max() * 1.05))

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha='right')

    # Add statistics
    mean_util = df['memory_utilization_pct'].mean()
    median_util = df['memory_utilization_pct'].median()

    ax.axhline(y=mean_util, color='red', linestyle='--', linewidth=1,
               alpha=0.7, label=f'Mean: {mean_util:.1f}%')
    ax.axhline(y=median_util, color='orange', linestyle='--', linewidth=1,
               alpha=0.7, label=f'Median: {median_util:.1f}%')

    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved to {output_file}")

    plt.close()

def plot_combined(df, output_file='utilization_combined.png'):
    """Plot CPU and memory on same chart"""
    print(f"\nCreating combined utilization chart...")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    # CPU plot
    ax1.plot(df['timestamp'], df['cpu_utilization_pct'],
            linewidth=0.5, alpha=0.7, color='#2E86AB', label='CPU')
    ax1.axhline(y=df['cpu_utilization_pct'].mean(), color='red',
                linestyle='--', linewidth=1, alpha=0.5)
    ax1.set_ylabel('CPU Utilization (%)', fontsize=12)
    ax1.set_title('Cluster Utilization Over Time', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, max(105, df['cpu_utilization_pct'].max() * 1.05))
    ax1.legend(loc='upper right')

    # Memory plot
    ax2.plot(df['timestamp'], df['memory_utilization_pct'],
            linewidth=0.5, alpha=0.7, color='#A23B72', label='Memory')
    ax2.axhline(y=df['memory_utilization_pct'].mean(), color='red',
                linestyle='--', linewidth=1, alpha=0.5)
    ax2.set_xlabel('Time', fontsize=12)
    ax2.set_ylabel('Memory Utilization (%)', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, max(105, df['memory_utilization_pct'].max() * 1.05))
    ax2.legend(loc='upper right')

    # Format x-axis
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved to {output_file}")

    plt.close()

def plot_distributions(df, output_file='utilization_distributions.png'):
    """Plot distribution histograms"""
    print(f"\nCreating distribution histograms...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # CPU distribution
    ax1.hist(df['cpu_utilization_pct'], bins=50,
            color='#2E86AB', alpha=0.7, edgecolor='black')
    ax1.axvline(df['cpu_utilization_pct'].mean(), color='red',
                linestyle='--', linewidth=2, label='Mean')
    ax1.axvline(df['cpu_utilization_pct'].median(), color='orange',
                linestyle='--', linewidth=2, label='Median')
    ax1.set_xlabel('CPU Utilization (%)', fontsize=12)
    ax1.set_ylabel('Frequency', fontsize=12)
    ax1.set_title('CPU Utilization Distribution', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Memory distribution
    ax2.hist(df['memory_utilization_pct'], bins=50,
            color='#A23B72', alpha=0.7, edgecolor='black')
    ax2.axvline(df['memory_utilization_pct'].mean(), color='red',
                linestyle='--', linewidth=2, label='Mean')
    ax2.axvline(df['memory_utilization_pct'].median(), color='orange',
                linestyle='--', linewidth=2, label='Median')
    ax2.set_xlabel('Memory Utilization (%)', fontsize=12)
    ax2.set_ylabel('Frequency', fontsize=12)
    ax2.set_title('Memory Utilization Distribution', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved to {output_file}")

    plt.close()

def plot_daily_aggregates(df, output_file='utilization_daily.png'):
    """Plot daily average utilization"""
    print(f"\nCreating daily aggregate chart...")

    # Group by day
    df['date'] = df['timestamp'].dt.date
    daily = df.groupby('date').agg({
        'cpu_utilization_pct': 'mean',
        'memory_utilization_pct': 'mean'
    }).reset_index()

    daily['date'] = pd.to_datetime(daily['date'])

    fig, ax = plt.subplots(figsize=(14, 6))

    ax.plot(daily['date'], daily['cpu_utilization_pct'],
            marker='o', linewidth=2, markersize=4,
            label='CPU', color='#2E86AB')
    ax.plot(daily['date'], daily['memory_utilization_pct'],
            marker='s', linewidth=2, markersize=4,
            label='Memory', color='#A23B72')

    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Average Utilization (%)', fontsize=12)
    ax.set_title('Daily Average Utilization', fontsize=14, fontweight='bold')

    ax.grid(True, alpha=0.3)
    ax.legend(loc='upper right', fontsize=12)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved to {output_file}")

    plt.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 visualize_utilization.py <timeseries_csv>")
        print("")
        print("Creates visualization charts from utilization time series data.")
        print("")
        print("Generates:")
        print("  - cpu_utilization_timeline.png")
        print("  - memory_utilization_timeline.png")
        print("  - utilization_combined.png")
        print("  - utilization_distributions.png")
        print("  - utilization_daily.png")
        sys.exit(1)

    timeseries_file = sys.argv[1]

    # Load data
    df = load_timeseries(timeseries_file)

    # Create charts
    print("\nGenerating visualizations...")
    print("="*60)

    plot_cpu_utilization(df)
    plot_memory_utilization(df)
    plot_combined(df)
    plot_distributions(df)
    plot_daily_aggregates(df)

    print("\n" + "="*60)
    print("VISUALIZATION COMPLETE")
    print("="*60)
    print("\nGenerated files:")
    print("  1. cpu_utilization_timeline.png    - CPU over time")
    print("  2. memory_utilization_timeline.png - Memory over time")
    print("  3. utilization_combined.png        - Both metrics")
    print("  4. utilization_distributions.png   - Histograms")
    print("  5. utilization_daily.png           - Daily averages")
    print("")
    print("All charts are publication-quality (300 DPI)")
    print("="*60)

if __name__ == '__main__':
    main()
