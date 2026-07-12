"""
Stock Comparison Tool — Core Logic
====================================
Compares stock levels between a WASP export and a Dynamics export, matching
on Item Number and reporting the minimum stock available in both systems.
"""

from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Business rules
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
    first. Accepts either a filesystem Path/str, or a file-like object with
    a `.name` attribute (e.g. a Streamlit UploadedFile)."""
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

    wasp_df = wasp_df.copy()
    wasp_df["Site"] = wasp_df["Site"].fillna("").astype(str).str.strip()
    filtered = wasp_df[wasp_df["Site"].isin(INCLUDED_SITES)]
    stats["after_site_filter"] = len(filtered)

    filtered = filtered.copy()
    filtered["Location"] = filtered["Location"].fillna("").astype(str)

    def location_excluded(location: str) -> bool:
        return any(pattern in location for pattern in EXCLUDED_LOCATION_PATTERNS)

    filtered = filtered[~filtered["Location"].apply(location_excluded)]
    stats["after_location_filter"] = len(filtered)

    filtered["Item Number"] = filtered["Item Number"].fillna("").astype(str).str.strip()
    filtered["Total Available"] = pd.to_numeric(filtered["Total Available"], errors="coerce").fillna(0)
    filtered = filtered[filtered["Item Number"] != ""]
    wasp_pivot = filtered.groupby("Item Number")["Total Available"].sum()

    dynamics_df = dynamics_df.copy()
    dynamics_df["Item number"] = dynamics_df["Item number"].fillna("").astype(str).str.strip()
    dynamics_df["Available for reservation"] = pd.to_numeric(
        dynamics_df["Available for reservation"], errors="coerce"
    ).fillna(0)
    dynamics_df = dynamics_df[dynamics_df["Item number"] != ""]
    dynamics_lookup = dynamics_df.set_index("Item number")["Available for reservation"].to_dict()

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
