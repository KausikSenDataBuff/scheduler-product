"""
Example Usage of the Scheduler Product Modules

This file demonstrates how to use all the modules together in a typical workflow.
"""

import pandas as pd
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from data_loader import load_data
from validator import validate_foreign_keys, validate_nulls
from job_builder import build_jobs, initialize_machine_state
from scheduler import run_scheduler, save_schedule, verify_schedule
from kpi import compute_completion, compute_kpi_metrics

def main():
    print("=== Example Usage of Scheduler Product Modules ===\n")

    # Step 1: Load data
    print("1. Loading data from CSV files...")
    data = load_data()
    print(f"   Loaded {len(data)} DataFrames:")
    for key, df in data.items():
        print(f"   - {key}: {df.shape[0]} rows, {df.shape[1]} columns")
    print()

    # Step 2: Validate data
    print("2. Validating data integrity...")
    try:
        validate_foreign_keys(data)
        print("   PASS: Foreign key validation passed")
    except ValueError as e:
        print(f"   FAIL: Foreign key validation failed: {e}")
        return

    try:
        validate_nulls(data)
        print("   PASS: Null value validation passed")
    except ValueError as e:
        print(f"   FAIL: Null value validation failed: {e}")
        return
    print()

    # Step 3: Build jobs
    print("3. Building operation-level jobs...")
    jobs_df = build_jobs(data)
    print(f"   Built {len(jobs_df)} job operations")
    print(f"   Columns: {list(jobs_df.columns)}")
    print("   Sample jobs:")
    print(jobs_df.head())
    print()

    # Step 4: Initialize machine state
    print("4. Initializing machine state...")
    machine_state = initialize_machine_state(data)
    print(f"   Initialized state for {len(machine_state)} machines")
    print(f"   Example machine states:")
    for i, (machine_id, jobs) in enumerate(list(machine_state.items())[:3]):
        print(f"     {machine_id}: {jobs} (length: {len(jobs)})")
    print()

    # Step 5: Run scheduler
    print("5. Running scheduling algorithm...")
    schedule_df = run_scheduler(data)
    print(f"   Scheduled {len(schedule_df)} operations")
    print(f"   Columns: {list(schedule_df.columns)}")
    print("   Sample scheduled operations:")
    print(schedule_df.head())
    print()

    # Step 6: Save schedule
    print("6. Saving schedule to CSV...")
    save_schedule(schedule_df)
    print()

    # Step 7: Verify schedule
    print("7. Verifying schedule correctness...")
    passed, errors = verify_schedule(schedule_df)
    if passed:
        print("   PASS: Schedule verification passed:")
        print("     - No machine has overlapping operations")
        print("     - Operation sequence order is respected per order")
    else:
        print("   FAIL: Schedule verification failed:")
        for error in errors[:5]:
            print(f"     - {error}")
        if len(errors) > 5:
            print(f"     ... and {len(errors) - 5} more errors")
        return
    print()

    # Step 8: Compute completion times and KPIs
    print("8. Computing completion times and KPIs...")

    # Compute completion times (with delay calculation)
    completion_df = compute_completion(schedule_df, data['orders'])
    print(f"   Computed completion times for {len(completion_df)} orders")
    print("   Sample completion times:")
    print(completion_df.head())
    print()

    # Compute KPI metrics
    kpi_metrics = compute_kpi_metrics(schedule_df, data['orders'])
    print("   Key Performance Indicators:")
    print(f"     Total Orders: {kpi_metrics['total_orders']}")
    print(f"     On-time Orders: {kpi_metrics['on_time_orders']}")
    print(f"     Late Orders: {kpi_metrics['late_orders']}")
    print(f"     Average Delay: {kpi_metrics['avg_delay']:.2f} hours")
    print(f"     Maximum Delay: {kpi_metrics['max_delay']:.2f} hours")
    print()

    # Additional insights
    print("9. Additional Insights:")
    early_orders = (completion_df['delay_hours'] < 0).sum()
    on_time_orders = (completion_df['delay_hours'] == 0).sum()
    late_orders = (completion_df['delay_hours'] > 0).sum()
    print(f"   Orders completed early: {early_orders}")
    print(f"   Orders completed exactly on time: {on_time_orders}")
    print(f"   Orders completed late: {late_orders}")
    print()

    # Show worst and best performing orders
    worst_late = completion_df.nlargest(3, 'delay_hours')[['order_id', 'delay_hours']]
    best_early = completion_df.nsmallest(3, 'delay_hours')[['order_id', 'delay_hours']]

    print("   Top 3 latest orders (worst delay):")
    for _, row in worst_late.iterrows():
        print(f"     Order {row['order_id']}: {row['delay_hours']:.2f} hours late")

    print("   Top 3 earliest orders (best performance):")
    for _, row in best_early.iterrows():
        print(f"     Order {row['order_id']}: {abs(row['delay_hours']):.2f} hours early")
    print()

    print("=== Example Usage Completed Successfully ===")

if __name__ == "__main__":
    main()