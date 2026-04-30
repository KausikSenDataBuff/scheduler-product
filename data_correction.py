"""
Data correction script for orders_phase2.csv

Fixes data quality issues where:
- release_time > due_date (set release_time = due_date - 1 day)
- material_available_time > due_date (set material_available_time = due_date - 1 day)

Ensures all orders have valid temporal constraints.
"""

import pandas as pd
import os

def fix_orders_phase2(input_path, output_path=None):
    """
    Load orders_phase2.csv and fix temporal constraint violations.

    Args:
        input_path: Path to orders_phase2.csv
        output_path: Path to save corrected file (optional, defaults to input_path if not provided)

    Returns:
        DataFrame with corrected data
    """
    if output_path is None:
        output_path = input_path

    print(f"Loading {input_path}...")
    df = pd.read_csv(input_path)

    # Parse datetime columns
    datetime_cols = ['order_date', 'due_date', 'release_time', 'material_available_time']
    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    print(f"Loaded {len(df)} orders")

    # Track corrections
    release_fixes = 0
    material_fixes = 0

    # Fix release_time > due_date
    mask_release = df['release_time'] > df['due_date']
    if mask_release.any():
        release_fixes = mask_release.sum()
        print(f"Found {release_fixes} orders with release_time > due_date")

        # Set release_time to due_date - 1 day for violated orders
        df.loc[mask_release, 'release_time'] = df.loc[mask_release, 'due_date'] - pd.Timedelta(days=1)
        print(f"  Fixed {release_fixes} release_time violations")

    # Fix material_available_time > due_date
    mask_material = df['material_available_time'] > df['due_date']
    if mask_material.any():
        material_fixes = mask_material.sum()
        print(f"Found {material_fixes} orders with material_available_time > due_date")

        # Set material_available_time to due_date - 1 day for violated orders
        df.loc[mask_material, 'material_available_time'] = df.loc[mask_material, 'due_date'] - pd.Timedelta(days=1)
        print(f"  Fixed {material_fixes} material_available_time violations")

    # Ensure release_time <= material_available_time <= due_date
    mask_release_after_material = df['release_time'] > df['material_available_time']
    if mask_release_after_material.any():
        fixes = mask_release_after_material.sum()
        print(f"Found {fixes} orders where release_time > material_available_time")
        # Swap them: set release_time = material_available_time - 1 hour (min feasible)
        df.loc[mask_release_after_material, 'release_time'] = df.loc[mask_release_after_material, 'material_available_time'] - pd.Timedelta(hours=1)
        print(f"  Fixed {fixes} release/material ordering issues")

    # Save corrected file
    print(f"\nSaving corrected data to {output_path}...")
    df.to_csv(output_path, index=False)

    total_fixes = release_fixes + material_fixes
    print(f"\n=== Summary ===")
    print(f"Total orders processed: {len(df)}")
    print(f"Total corrections made: {total_fixes}")
    print(f"  - release_time fixes: {release_fixes}")
    print(f"  - material_available_time fixes: {material_fixes}")

    return df


def fix_orders_multilevel(input_path, output_path=None):
    """
    Load orders_multilevel.csv and fix temporal constraint violations.

    Same logic as fix_orders_phase2 but for multi-level orders.
    """
    if output_path is None:
        output_path = input_path

    print(f"Loading {input_path}...")
    df = pd.read_csv(input_path)

    # Parse datetime columns
    datetime_cols = ['order_date', 'due_date', 'release_time', 'material_available_time']
    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    print(f"Loaded {len(df)} multi-level orders")

    # Track corrections
    release_fixes = 0
    material_fixes = 0

    # Fix release_time > due_date
    mask_release = df['release_time'] > df['due_date']
    if mask_release.any():
        release_fixes = mask_release.sum()
        print(f"Found {release_fixes} orders with release_time > due_date")
        df.loc[mask_release, 'release_time'] = df.loc[mask_release, 'due_date'] - pd.Timedelta(days=1)
        print(f"  Fixed {release_fixes} release_time violations")

    # Fix material_available_time > due_date
    mask_material = df['material_available_time'] > df['due_date']
    if mask_material.any():
        material_fixes = mask_material.sum()
        print(f"Found {material_fixes} orders with material_available_time > due_date")
        df.loc[mask_material, 'material_available_time'] = df.loc[mask_material, 'due_date'] - pd.Timedelta(days=1)
        print(f"  Fixed {material_fixes} material_available_time violations")

    # Ensure release_time <= material_available_time
    mask_release_after_material = df['release_time'] > df['material_available_time']
    if mask_release_after_material.any():
        fixes = mask_release_after_material.sum()
        print(f"Found {fixes} orders where release_time > material_available_time")
        df.loc[mask_release_after_material, 'release_time'] = df.loc[mask_release_after_material, 'material_available_time'] - pd.Timedelta(hours=1)
        print(f"  Fixed {fixes} release/material ordering issues")

    # Save corrected file
    print(f"\nSaving corrected data to {output_path}...")
    df.to_csv(output_path, index=False)

    total_fixes = release_fixes + material_fixes
    print(f"\n=== Summary ===")
    print(f"Total orders processed: {len(df)}")
    print(f"Total corrections made: {total_fixes}")

    return df


if __name__ == "__main__":
    import sys

    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')

    # Fix orders_phase2.csv
    orders_phase2_input = os.path.join(data_dir, 'orders_phase2.csv')
    orders_phase2_output = os.path.join(data_dir, 'orders_phase2.csv')

    if os.path.exists(orders_phase2_input):
        print("=" * 50)
        print("Processing orders_phase2.csv")
        print("=" * 50)
        fix_orders_phase2(orders_phase2_input, orders_phase2_output)
    else:
        print(f"File not found: {orders_phase2_input}")

    # Fix orders_multilevel.csv
    orders_multi_input = os.path.join(data_dir, 'orders_multilevel.csv')
    orders_multi_output = os.path.join(data_dir, 'orders_multilevel.csv')

    if os.path.exists(orders_multi_input):
        print("\n" + "=" * 50)
        print("Processing orders_multilevel.csv")
        print("=" * 50)
        fix_orders_multilevel(orders_multi_input, orders_multi_output)
    else:
        print(f"File not found: {orders_multi_input}")

    print("\n=== Data correction complete ===")
