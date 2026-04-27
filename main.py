import pandas as pd
import os
from data_loader import load_data
from validator import validate_foreign_keys, validate_nulls
from job_builder import build_jobs, initialize_machine_state
from scheduler import run_scheduler, save_schedule
from kpi import compute_kpi_metrics

def plot_gantt(schedule_df, orders_df=None):
    """
    Plot a Gantt chart of the schedule.

    Args:
        schedule_df (pandas.DataFrame): DataFrame with columns:
                                        order_id, operation_seq, machine_id, start, end
        orders_df (pandas.DataFrame, optional): DataFrame with order information, must contain
                                                'order_id' and 'due_date' columns.
                                                If provided, due dates will be shown as vertical lines.
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        from datetime import datetime
    except ImportError:
        print("Matplotlib is not installed. Skipping Gantt chart plot.")
        return

    # Ensure the start and end columns are datetime
    df = schedule_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['start']):
        df['start'] = pd.to_datetime(df['start'])
    if not pd.api.types.is_datetime64_any_dtype(df['end']):
        df['end'] = pd.to_datetime(df['end'])

    # Get unique machines and sort them for consistent y-axis
    machines = sorted(df['machine_id'].unique())
    machine_to_y = {machine: i for i, machine in enumerate(machines)}

    # Create the figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))

    # Define colors for different orders (we'll use a colormap)
    # We'll assign a color per order_id for simplicity
    unique_orders = df['order_id'].unique()
    # Use a colormap to get distinct colors
    colors = plt.cm.Set3(range(len(unique_orders)))
    order_to_color = {order: colors[i] for i, order in enumerate(unique_orders)}

    # Plot each operation as a horizontal bar
    for _, row in df.iterrows():
        machine_y = machine_to_y[row['machine_id']]
        start = row['start']
        end = row['end']
        duration = end - start

        # Convert to matplotlib dates if needed, but we can use datetime objects directly
        # For barh, we need the duration as a number (in days since matplotlib dates are days)
        duration_days = duration.total_seconds() / (24 * 3600)  # Convert seconds to days

        ax.barh(machine_y, duration_days, left=start, height=0.8,
                align='center', color=order_to_color[row['order_id']], edgecolor='black')
        # Add text label for order_id and operation_seq if there's enough space
        if duration.total_seconds() > 30*60:  # Only label if operation is longer than 30 minutes
            # Text position: middle of the bar
            text_position = start + duration/2
            ax.text(text_position, machine_y,
                    f"{row['order_id']}\nOp{row['operation_seq']}",
                    ha='center', va='center', fontsize=8, color='black')

    # If orders_df is provided, add vertical lines for due dates
    if orders_df is not None:
        # Ensure due_date is datetime
        if not pd.api.types.is_datetime64_any_dtype(orders_df['due_date']):
            orders_df = orders_df.copy()
            orders_df['due_date'] = pd.to_datetime(orders_df['due_date'])
        # For each order, draw a vertical line at the due date
        for _, order_row in orders_df.iterrows():
            due_date = order_row['due_date']
            order_id = order_row['order_id']
            # We'll draw the line across all machines
            ax.axvline(x=due_date, color='red', linestyle='--', alpha=0.7, linewidth=1)
            # Add a text label for the due date at the top
            ax.text(due_date, len(machines), f"Due: {order_id}",
                    rotation=90, verticalalignment='bottom',
                    fontsize=8, color='red', alpha=0.7)

    # Customize the chart
    ax.set_yticks(range(len(machines)))
    ax.set_yticklabels(machines)
    ax.set_xlabel('Time')
    ax.set_ylabel('Machine')
    ax.set_title('Production Schedule Gantt Chart')
    ax.grid(True, axis='x', linestyle='--', alpha=0.5)

    # Create a legend for order colors (if there are not too many orders)
    if len(unique_orders) <= 20:
        legend_patches = [mpatches.Patch(color=order_to_color[order], label=order)
                          for order in unique_orders[:20]]  # Limit to 20 for clarity
        ax.legend(handles=legend_patches, title="Order ID",
                  loc='upper right', bbox_to_anchor=(1.15, 1))

    # Adjust layout to prevent clipping of labels
    plt.tight_layout()

    # Save the figure
    output_file = 'gantt_chart.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print("Gantt chart saved as 'gantt_chart.png'")

    # Show the plot (optional, depending on environment)
    # plt.show()
    plt.close()  # Close the figure to free memory

def main():
    print("=== Starting Production Scheduling Workflow ===")

    try:
        # Step 1: Load data
        print("\n1. Loading data...")
        data = load_data()
        print(f"   Loaded {len(data)} DataFrames")
        print(f"   Orders: {len(data['orders'])} rows")
        print(f"   Machines: {len(data['machines'])} rows")
        print(f"   Products: {len(data['products'])} rows")
        print(f"   Routing: {len(data['routing'])} rows")

        # Step 2: Run validations
        print("\n2. Running validations...")
        validate_foreign_keys(data)
        validate_nulls(data)
        print("   All validations passed")

        # Step 3: Build jobs
        print("\n3. Building jobs...")
        jobs_df = build_jobs(data)
        print(f"   Built {len(jobs_df)} job operations")
        print(f"   Columns: {list(jobs_df.columns)}")

        # Step 4: Initialize machines
        print("\n4. Initializing machine state...")
        machine_state = initialize_machine_state(data)
        print(f"   Initialized state for {len(machine_state)} machines")
        print(f"   Example: {list(machine_state.items())[0]}")

        # Step 5: Run scheduler
        print("\n5. Running scheduler...")
        schedule_df = run_scheduler(data)
        print(f"   Scheduled {len(schedule_df)} operations")
        print(f"   Columns: {list(schedule_df.columns)}")

        # Step 6: Save schedule
        print("\n6. Saving schedule...")
        save_schedule(schedule_df)
        print("   Schedule saved to schedule.csv")

        # Step 7: Compute KPIs
        print("\n7. Computing KPIs...")
        kpi_metrics = compute_kpi_metrics(schedule_df, data['orders'])
        print("   KPI Metrics:")
        for key, value in kpi_metrics.items():
            if key in ['avg_delay', 'max_delay']:
                print(f"     {key}: {value:.2f} hours")
            else:
                print(f"     {key}: {value}")

        # Step 8: Plot Gantt chart
        print("\n8. Plotting Gantt chart...")
        plot_gantt(schedule_df, data['orders'])

        print("\n=== Workflow Completed Successfully ===")

    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit(main())