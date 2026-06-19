import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ==========================================
# PAGE CONFIGURATION & UI SETUP
# ==========================================
st.set_page_config(page_title="Catalog Integrity Check", layout="wide")

st.title("🛒 Catalog Integrity Checker")
st.markdown("""
**Operational Guardrail:** Upload the latest active exports from Shopify and Dynamics 365. 
This tool cross-references inventory and lifecycle statuses to generate an instant bulk-import fix file, preventing phantom inventory and overselling.
""")

st.divider()

# ==========================================
# SIDEBAR CONFIGURATION
# ==========================================
with st.sidebar:
    st.header("⚙️ Configuration")
    inventory_buffer = st.number_input(
        "Inventory Buffer Threshold", 
        min_value=0, value=1, 
        help="If D365 stock is at or below this number, the item will be drafted."
    )
    discontinued_keyword = st.text_input(
        "D365 Discontinued Keyword", 
        value="Discontinued",
        help="The exact text D365 uses for dead items."
    )

# ==========================================
# FILE UPLOADERS
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Shopify Export")
    shopify_file = st.file_uploader("Upload shopify_export.csv", type=['csv'])

with col2:
    st.subheader("2. Upload D365 Export")
    d365_file = st.file_uploader("Upload d365_export.csv", type=['csv'])

# ==========================================
# EXECUTION LOGIC
# ==========================================
if shopify_file is not None and d365_file is not None:
    
    # Read the files
    try:
        df_shopify = pd.read_csv(shopify_file)
        df_d365 = pd.read_csv(d365_file)
    except Exception as e:
        st.error(f"Error reading files: {e}")
        st.stop()

    # Verify required columns exist (using the dummy names from our previous test)
    req_shopify_cols = ['Handle', 'SKU', 'Status']
    req_d365_cols = ['SKU', 'Available_Quantity', 'Item_Status']
    
    missing_shopify = [col for col in req_shopify_cols if col not in df_shopify.columns]
    missing_d365 = [col for col in req_d365_cols if col not in df_d365.columns]
    
    if missing_shopify or missing_d365:
        st.error("⚠️ Column Mismatch Detected!")
        if missing_shopify:
            st.write(f"Missing in Shopify export: {missing_shopify}")
        if missing_d365:
            st.write(f"Missing in D365 export: {missing_d365}")
        st.info("Please ensure your CSVs match the required formatting.")
        st.stop()

    if st.button("🚀 Run Integrity Check", use_container_width=True, type="primary"):
        with st.spinner("Crunching data..."):
            
            # Merge on SKU
            df_merged = pd.merge(df_shopify, df_d365, on='SKU', how='inner')
            
            # Logic Engine
            def determine_new_status(row):
                if str(row['Status']).strip().lower() == 'active':
                    # Rule 1: Discontinued
                    if str(row['Item_Status']).strip().lower() == discontinued_keyword.lower():
                        return 'Archived'
                    # Rule 2: Stock Risk
                    try:
                        if float(row['Available_Quantity']) <= inventory_buffer:
                            return 'Draft'
                    except ValueError:
                        pass
                return None

            df_merged['New_Status'] = df_merged.apply(determine_new_status, axis=1)
            df_action_needed = df_merged[df_merged['New_Status'].notnull()].copy()
            
            # ==========================================
            # DASHBOARD & RESULTS
            # ==========================================
            st.divider()
            st.subheader("📊 Executive Summary")
            
            metric_col1, metric_col2, metric_col3 = st.columns(3)
            
            total_evaluated = len(df_merged)
            total_drafted = len(df_action_needed[df_action_needed['New_Status'] == 'Draft'])
            total_archived = len(df_action_needed[df_action_needed['New_Status'] == 'Archived'])
            
            metric_col1.metric("Total SKUs Evaluated", total_evaluated)
            metric_col2.metric("Drafted (Stock Risk)", total_drafted, delta="-Overselling Prevented", delta_color="normal")
            metric_col3.metric("Archived (Discontinued)", total_archived, delta="-Cleaned Catalog", delta_color="normal")
            
            # Generate the Fix File
            df_final = df_action_needed[['Handle', 'New_Status']].copy()
            df_final.rename(columns={'New_Status': 'Status'}, inplace=True)
            
            if len(df_final) > 0:
                st.success(f"**{len(df_final)} Anomalies Detected.** The fix file is ready for Shopify import.")
                
                # Convert DF to CSV in memory for download button
                csv_buffer = io.StringIO()
                df_final.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()
                
                date_str = datetime.now().strftime("%Y%m%d_%H%M")
                filename = f"Shopify_Import_Fix_{date_str}.csv"
                
                # Layout for download button and data preview
                dl_col, preview_col = st.columns([1, 2])
                with dl_col:
                    st.download_button(
                        label="⬇️ Download Shopify Import File",
                        data=csv_data,
                        file_name=filename,
                        mime='text/csv',
                        type="primary"
                    )
                with preview_col:
                    with st.expander("Preview Actionable Items"):
                        st.dataframe(df_action_needed[['SKU', 'Handle', 'Available_Quantity', 'Item_Status', 'New_Status']], use_container_width=True)
            else:
                st.success("✅ No anomalies found. The catalog is perfectly synced with D365.")
