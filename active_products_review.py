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
Map your columns dynamically below to generate an instant bulk-import fix file, preventing phantom inventory and overselling.
""")

st.divider()

# ==========================================
# SIDEBAR CONFIGURATION (BUSINESS RULES)
# ==========================================
with st.sidebar:
    st.header("⚙️ Business Rules")
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
# 1. FILE UPLOADERS
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload Shopify Export")
    shopify_file = st.file_uploader("Upload shopify_export.csv", type=['csv'])

with col2:
    st.subheader("2. Upload D365 Export")
    d365_file = st.file_uploader("Upload d365_export.csv", type=['csv'])

# ==========================================
# 2. DYNAMIC COLUMN MAPPING & EXECUTION
# ==========================================
if shopify_file is not None and d365_file is not None:
    
    # Read the files
    try:
        df_shopify = pd.read_csv(shopify_file)
        df_d365 = pd.read_csv(d365_file)
    except Exception as e:
        st.error(f"Error reading files: {e}")
        st.stop()

    st.divider()
    st.subheader("3. Map Data Columns")
    st.markdown("The system has tried to auto-detect the correct columns. Please verify before running.")

    # Helper function to auto-guess the right column dropdown index
    def get_default_index(columns_list, guess_words):
        for i, col in enumerate(columns_list):
            if any(guess.lower() in str(col).lower() for guess in guess_words):
                return i
        return 0

    map_col1, map_col2 = st.columns(2)

    with map_col1:
        st.markdown("**🛍️ Shopify Data**")
        shop_cols = list(df_shopify.columns)
        shop_handle_col = st.selectbox("Which column is the Handle?", shop_cols, index=get_default_index(shop_cols, ['handle']))
        shop_sku_col = st.selectbox("Which column is the SKU?", shop_cols, index=get_default_index(shop_cols, ['sku']))
        shop_status_col = st.selectbox("Which column is the Status?", shop_cols, index=get_default_index(shop_cols, ['status', 'state', 'active']))

    with map_col2:
        st.markdown("**🏢 D365 Data**")
        d365_cols = list(df_d365.columns)
        d365_sku_col = st.selectbox("Which column is the D365 SKU?", d365_cols, index=get_default_index(d365_cols, ['sku', 'item', 'number']))
        d365_qty_col = st.selectbox("Which column is Available Quantity?", d365_cols, index=get_default_index(d365_cols, ['qty', 'quantity', 'stock', 'available']))
        d365_status_col = st.selectbox("Which column is Item Status?", d365_cols, index=get_default_index(d365_cols, ['status', 'lifecycle', 'state']))

    # ==========================================
    # 3. LOGIC ENGINE
    # ==========================================
    st.write("") # Spacer
    if st.button("🚀 Run Integrity Check", use_container_width=True, type="primary"):
        with st.spinner("Cross-referencing catalogs..."):
            
            # Merge dynamically based on user selections
            df_merged = pd.merge(
                df_shopify, 
                df_d365, 
                left_on=shop_sku_col, 
                right_on=d365_sku_col, 
                how='inner'
            )
            
            # Logic Engine using dynamic columns
            def determine_new_status(row):
                if str(row[shop_status_col]).strip().lower() == 'active':
                    # Rule 1: Discontinued
                    if str(row[d365_status_col]).strip().lower() == discontinued_keyword.lower():
                        return 'Archived'
                    # Rule 2: Stock Risk
                    try:
                        if float(row[d365_qty_col]) <= inventory_buffer:
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
            
            metric_col1.metric("Total SKUs Cross-Referenced", total_evaluated)
            metric_col2.metric("Drafted (Stock Risk)", total_drafted, delta="-Overselling Prevented", delta_color="normal")
            metric_col3.metric("Archived (Discontinued)", total_archived, delta="-Cleaned Catalog", delta_color="normal")
            
            # Generate the Fix File using dynamic handle column
            df_final = df_action_needed[[shop_handle_col, 'New_Status']].copy()
            
            # Shopify strictly requires the header to be "Handle" and "Status" for imports
            df_final.rename(columns={shop_handle_col: 'Handle', 'New_Status': 'Status'}, inplace=True)
            
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
                        # Show the user a preview using the columns they selected
                        preview_cols = [shop_sku_col, shop_handle_col, d365_qty_col, d365_status_col, 'New_Status']
                        st.dataframe(df_action_needed[preview_cols], use_container_width=True)
            else:
                st.success("✅ No anomalies found. The catalog is perfectly synced with D365.")
