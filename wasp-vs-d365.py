"""
Stock Comparison Tool — Streamlit App
======================================
Web version of the WASP vs. Dynamics stock comparison tool. Upload both
files, click Compare, review the results, and download an Excel file.

Run locally:
    streamlit run app.py

The comparison logic itself lives in stock_logic.py so it can be reused
by both this app and the command-line script (stock_comparison_cli.py).
"""

import io
from datetime import date

import pandas as pd
import streamlit as st

from stock_logic import compare_stock, load_table

st.set_page_config(page_title="Stock Comparison Tool", page_icon="📦", layout="wide")

st.title("📦 Stock Comparison Tool")
st.write("Upload your WASP and Dynamics files to compare stock levels.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. WASP File")
    st.caption("Contains: Item Number, Description, Total Available, Location, Site")
    wasp_file = st.file_uploader(
        "Upload WASP file", type=["xlsx", "xls", "csv"], key="wasp_uploader"
    )

with col2:
    st.subheader("2. Dynamics File")
    st.caption("Contains: Item number, Available for reservation")
    dynamics_file = st.file_uploader(
        "Upload Dynamics file", type=["xlsx", "xls", "csv"], key="dynamics_uploader"
    )

compare_clicked = st.button(
    "🔍 Compare Stock", type="primary", disabled=not (wasp_file and dynamics_file)
)

if compare_clicked:
    try:
        with st.spinner("Reading files..."):
            wasp_df = load_table(wasp_file)
            dynamics_df = load_table(dynamics_file)

        with st.spinner("Comparing stock..."):
            result_df, stats = compare_stock(wasp_df, dynamics_df)

        st.session_state["result_df"] = result_df
        st.session_state["stats"] = stats

    except ValueError as e:
        st.error(f"⚠️ {e}")
        st.session_state.pop("result_df", None)
        st.session_state.pop("stats", None)
    except Exception as e:
        st.error(f"⚠️ Something went wrong while reading or comparing the files: {e}")
        st.session_state.pop("result_df", None)
        st.session_state.pop("stats", None)

# Show results if we have them (persists across reruns, e.g. after clicking Download)
if "result_df" in st.session_state:
    result_df = st.session_state["result_df"]
    stats = st.session_state["stats"]

    st.divider()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📊 Original WASP rows", stats["original_wasp_rows"])
    m2.metric("✅ After site filter", stats["after_site_filter"])
    m3.metric("🚫 After location filter", stats["after_location_filter"])
    m4.metric("✅ Final matched", stats["final_matched"])

    if result_df.empty:
        st.info("No matching items with positive stock in both files.")
    else:
        st.dataframe(result_df, use_container_width=True, hide_index=True)

        # Build the Excel file in memory for download
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            result_df.to_excel(writer, index=False, sheet_name="Comparison")
        buffer.seek(0)

        st.download_button(
            label="📥 Export to Excel",
            data=buffer,
            file_name=f"stock_comparison_{date.today().isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
