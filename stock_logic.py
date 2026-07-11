#!/usr/bin/env python3
"""
Stock Comparison Tool
======================
Compares stock levels between a WASP export and a Dynamics export, matching
on Item Number and reporting the minimum stock available in both systems.

This is a Python conversion of an offline HTML/JS tool. The original tool
used a hand-written Excel (.xlsx) parser that could not correctly decompress
real Excel files (it didn't implement Huffman decoding, only "stored"/
uncompressed blocks). This version uses pandas + openpyxl, which read
real-world .xlsx and .csv files correctly.

USAGE
-----
    python stock_comparison.py <wasp_file> <dynamics_file> [-o output.xlsx]

Both <wasp_file> and <dynamics_file> can be .xlsx, .xls, or .csv.

WASP file must contain columns: Item Number, Total Available, Location, Site
Dynamics file must contain columns: Item number, Available for reservation

EXAMPLE
-------
    python stock_comparison.py wasp_export.xlsx dynamics_export.xlsx -o comparison.xlsx
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Business rules (carried over unchanged from the original HTML tool)
# ---------------------------------------------------------------------------

INCLUDED_SITES = [
    "ABQ1", "ABQ1RE", "ABQ2", "ABQ3", "ABQ4", "ABQ5", "ABQ6", "ABQRE",
    "CW", "CW2", "CW3", "CW4", "CW5",
]

EXCLUDED_LOCATION_PATTERNS = [
    "-0", "-M", "-H", "-N", "-E",
    " 0", " M", " H", " N", " E",
    "IS", "MI", "OF", "SH", "PO", "FAB", "U", "GLA",
    "060", "PART", "LEG", "1PE", "GCC", "DAM", "MAR", "HAN", "BOL", "/",
]


# ---------------------------------------------------------------------------
# File loading
# ---------------------------------------------------------------------------

def load_table(file) -> pd.DataFrame:
    """Load a .xlsx, .xls, or .csv file into a DataFrame, all columns as text
    first (we convert numeric columns explicitly later, same as the original
    tool did with parseFloat).

    Accepts either a filesystem Path/str, or a file-like object with a
    `.name` attribute (e.g. a Streamlit UploadedFile)."""
    name = file.name if hasattr(file, "name") else str(file)
    suffix = Path(name).suffix.lower()
    if suffix in (".xlsx", ".xls"):
        return pd.read_excel(file, dtype=str)
    elif suffix == ".csv":
        return pd.read_csv(file, dtype=str)
    else:
        raise ValueError(
            f"Unsupported file type '{suffix}' for {name}. "
            "Please provide a .xlsx, .xls, or .csv file."
        )


def require_columns(df: pd.DataFrame, columns: list[str], file_label: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(
            f"{file_label} is missing required column(s): {', '.join(missing)}. "
            f"Found columns: {', '.join(df.columns)}"
        )


# ---------------------------------------------------------------------------
# Core comparison logic
# ---------------------------------------------------------------------------

def compare_stock(wasp_df: pd.DataFrame, dynamics_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    require_columns(wasp_df, ["Item Number", "Total Available", "Location", "Site"], "WASP file")
    require_columns(dynamics_df, ["Item number", "Available for reservation"], "Dynamics file")

    stats = {"original_wasp_rows": len(wasp_df)}

    # Step 1: filter WASP to included sites only
    wasp_df = wasp_df.copy()
    wasp_df["Site"] = wasp_df["Site"].fillna("").astype(str).str.strip()
    filtered = wasp_df[wasp_df["Site"].isin(INCLUDED_SITES)]
    stats["after_site_filter"] = len(filtered)

    # Step 2: exclude rows whose Location contains any excluded pattern
    filtered = filtered.copy()
    filtered["Location"] = filtered["Location"].fillna("").astype(str)

    def location_excluded(location: str) -> bool:
        return any(pattern in location for pattern in EXCLUDED_LOCATION_PATTERNS)

    filtered = filtered[~filtered["Location"].apply(location_excluded)]
    stats["after_location_filter"] = len(filtered)

    # Step 3: pivot - sum Total Available by Item Number
    filtered["Item Number"] = filtered["Item Number"].fillna("").astype(str).str.strip()
    filtered["Total Available"] = pd.to_numeric(filtered["Total Available"], errors="coerce").fillna(0)
    filtered = filtered[filtered["Item Number"] != ""]
    wasp_pivot = filtered.groupby("Item Number")["Total Available"].sum()

    # Step 4: build Dynamics lookup
    dynamics_df = dynamics_df.copy()
    dynamics_df["Item number"] = dynamics_df["Item number"].fillna("").astype(str).str.strip()
    dynamics_df["Available for reservation"] = pd.to_numeric(
        dynamics_df["Available for reservation"], errors="coerce"
    ).fillna(0)
    dynamics_df = dynamics_df[dynamics_df["Item number"] != ""]
    # If an item number appears more than once in Dynamics, last one wins,
    # matching the original tool's plain object-key-overwrite behavior.
    dynamics_lookup = dynamics_df.set_index("Item number")["Available for reservation"].to_dict()

    # Step 5: match and compare
    rows = []
    for item_num, wasp_stock in wasp_pivot.items():
        if item_num not in dynamics_lookup:
            continue
        dyn_stock = dynamics_lookup[item_num]
        if wasp_stock <= 0 or dyn_stock <= 0:
            continue
        rows.append(
            {
                "Item Number": item_num,
                "WASP Stock": wasp_stock,
                "Dynamics Stock": dyn_stock,
                "Min Stock": min(wasp_stock, dyn_stock),
            }
        )

    result_df = pd.DataFrame(rows, columns=["Item Number", "WASP Stock", "Dynamics Stock", "Min Stock"])
    result_df = result_df.sort_values("Item Number").reset_index(drop=True)

    stats["final_matched"] = len(result_df)
    return result_df, stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

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
