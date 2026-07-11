#!/usr/bin/env python3
"""
Stock Comparison Tool — Command Line
======================================
    python stock_comparison_cli.py <wasp_file> <dynamics_file> [-o output.xlsx]

Both <wasp_file> and <dynamics_file> can be .xlsx, .xls, or .csv.
For the web version, see app.py (run with `streamlit run app.py`).
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

from stock_logic import compare_stock, load_table


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare WASP and Dynamics stock levels.")
    parser.add_argument("wasp_file", type=Path, help="Path to the WASP export (.xlsx/.xls/.csv)")
    parser.add_argument("dynamics_file", type=Path, help="Path to the Dynamics export (.xlsx/.xls/.csv)")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output file path (.xlsx or .csv). Defaults to stock_comparison_<date>.xlsx",
    )
    args = parser.parse_args()

    for f in (args.wasp_file, args.dynamics_file):
        if not f.exists():
            print(f"Error: file not found: {f}", file=sys.stderr)
            sys.exit(1)

    try:
        wasp_df = load_table(args.wasp_file)
        dynamics_df = load_table(args.dynamics_file)
        result_df, stats = compare_stock(wasp_df, dynamics_df)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Original WASP rows:     {stats['original_wasp_rows']}")
    print(f"After site filter:      {stats['after_site_filter']}")
    print(f"After location filter:  {stats['after_location_filter']}")
    print(f"Final matched items:    {stats['final_matched']}")
    print()

    if result_df.empty:
        print("No matching items with positive stock in both files.")
        return

    print(result_df.to_string(index=False))

    output_path = args.output
    if output_path is None:
        date_str = pd.Timestamp.today().strftime("%Y-%m-%d")
        output_path = Path(f"stock_comparison_{date_str}.xlsx")

    if output_path.suffix.lower() == ".csv":
        result_df.to_csv(output_path, index=False)
    else:
        result_df.to_excel(output_path, index=False)

    print(f"\nSaved results to: {output_path}")


if __name__ == "__main__":
    main()
