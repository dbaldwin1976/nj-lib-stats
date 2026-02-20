import streamlit as st
import pandas as pd
import os
import altair as alt

st.set_page_config(layout="wide", page_title="NJ Library Stats Dashboard")

# --- 1. DATA LOADING ENGINE ---
@st.cache_data
def load_all_data(folder_path):
    all_files = [f for f in os.listdir(folder_path) if f.endswith('.xlsx')]
    df_list = []
    
    for file in all_files:
        year = file.split('.')[0]
        file_path = os.path.join(folder_path, file)
        
        # Load data and clean column names immediately
        temp_df = pd.read_excel(file_path)
        temp_df.columns = [str(c).strip() for c in temp_df.columns]
        temp_df['Data_Year'] = year
        df_list.append(temp_df)
    
    return pd.concat(df_list, ignore_index=True)

# Path to your 'data' folder on the Chromebook/GitHub
data_folder = "data"

if not os.path.exists(data_folder):
    st.error(f"Folder '{data_folder}' not found. Please ensure your Excel files are in a folder named 'data'.")
else:
    master_df = load_all_data(data_folder)
    
    # Identify the library name column (usually the first or one with 'LEGAL'/'NAME')
    target_col = master_df.columns[0] 

    st.title("📊 NJ Library Statistics Explorer")

    tab1, tab2, tab3, tab4 = st.tabs(["Snapshot", "History", "Compare", "Full Data"])

    # --- TAB 1: INDIVIDUAL LIBRARY SNAPSHOT ---
    with tab1:
        c1, c2 = st.columns(2)
        lib_list = sorted(master_df[target_col].dropna().unique())
        
        selected_lib = c1.selectbox("Select Municipality", lib_list, key="snap_lib")
        selected_year = c2.selectbox("Select Year", sorted(master_df['Data_Year'].unique(), reverse=True), key="snap_yr")
        
        snap = master_df[(master_df[target_col] == selected_lib) & (master_df['Data_Year'] == selected_year)]
        
        if not snap.empty:
            st.subheader(f"📊 {selected_lib} ({selected_year})")
            
            # Get True Column Order from the specific file
            true_file_path = os.path.join(data_folder, f"{selected_year}.xlsx")
            raw_excel_cols = pd.read_excel(true_file_path, nrows=0).columns.tolist()
            raw_excel_cols = [str(c).strip() for c in raw_excel_cols]
            
            display_df = snap.copy()

            # Formatting Loop
            for col in display_df.columns:
                val = display_df[col].values[0]
                if "ZIP" in col.upper():
                    try: display_df[col] = str(int(float(val))).zfill(5)
                    except: display_df[col] = str(val)
                elif "COUNTY CODE" in col.upper():
                    try: display_df[col] = str(int(float(val)))
                    except: display_df[col] = str(val)
                else:
                    try:
                        num_val = float(val)
                        display_df[col] = f"{num_val:,.0f}" if not pd.isna(num_val) else "N/A"
                    except:
                        display_df[col] = str(val)

            vertical_df = display_df.T
            vertical_df.columns = ["Value"]
            
            # Reorder based on Excel file
            existing_cols = [c for c in raw_excel_cols if c in vertical_df.index]
            vertical_df = vertical_df.loc[existing_cols]
            
            # Hide empty rows
            vertical_df = vertical_df[~vertical_df["Value"].astype(str).isin(["N/A", "nan", "None", ""])]
            st.table(vertical_df)

    # --- TAB 2: HISTORICAL TRENDS ---
    with tab2:
        st.header("📈 Historical Trend Analysis")
        
        c1, c2, c3 = st.columns(3)
        lib_list_hist = sorted(master_df[target_col].dropna().unique())
        selected_lib_hist = c1.selectbox("Select Library", lib_list_hist, key="hist_lib")
        
        lib_years = sorted(master_df[master_df[target_col] == selected_lib_hist]['Data_Year'].unique(), reverse=True)
        end_year = c2.selectbox("End Year", lib_years, key="hist_end_yr")
        
        all_cols = [c for c in master_df.columns if c not in ['Data_Year', target_col]]
        selected_metrics = c3.multiselect("Select Data Points", all_cols, default=[all_cols[0]] if all_cols else None)

        current_index = lib_years.index(end_year)
        five_years_or_less = lib_years[current_index : current_index + 5]

        hist_data = master_df[
            (master_df[target_col] == selected_lib_hist) & 
            (master_df['Data_Year'].isin(five_years_or_less))
        ].copy()

        if not hist_data.empty and selected_metrics:
            # Table View
            table_display = hist_data[['Data_Year'] + selected_metrics].copy()
            for col in selected_metrics:
                if "ZIP" in col.upper():
                    table_display[col] = table_display[col].apply(lambda x: str(int(float(x))).zfill(5) if pd.notnull(x) else "")
                elif "COUNTY CODE" in col.upper():
                    table_display[col] = table_display[col].apply(lambda x: str(int(float(x))) if pd.notnull(x) else "")
                else:
                    table_display[col] = pd.to_numeric(table_display[col], errors='coerce').apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "N/A")

            hist_pivot = table_display.set_index('Data_Year').T
            existing_years_in_order = [y for y in five_years_or_less if y in hist_pivot.columns]
            st.table(hist_pivot[existing_years_in_order])
            
            # Charting Section
            st.divider()
            st.subheader("📈 Visual Trends")
            
            chart_df = hist_data[['Data_Year'] + selected_metrics].copy()
            chart_df['Data_Year'] = pd.to_numeric(chart_df['Data_Year'], errors='coerce').astype(int)
            
            # Fix for period/number headers
            clean_name_map = {m: f"Metric_{i+1}" for i, m in enumerate(selected_metrics)}
            display_name_map = {v: k for k, v in clean_name_map.items()}
            chart_df = chart_df.rename(columns=clean_name_map)
            
            chart_df_melted = chart_df.melt('Data_Year', var_name='Metric', value_name='Value')

            if not chart_df_melted.empty:
                final_chart = alt.Chart(chart_df_melted).mark_line(point=True).encode(
                    x=alt.X('Data_Year:O', title='Year', sort='ascending'),
                    y=alt.Y('Value:Q', title='Value'),
                    color='Metric:N',
                    tooltip=['Data_Year', 'Metric', 'Value']
                ).properties(width='container', height=400)

                st.altair_chart(final_chart, use_container_width=True)

                for clean_name, original_name in display_name_map.items():
                    st.caption(f"**{clean_name}**: {original_name}")

    # --- TAB 3: PLACEHOLDER FOR COMPARISON ---
    with tab3:
        st.info("Comparison Tab code will be added next.")

    # --- TAB 4: RAW DATA ---
    with tab4:
        st.dataframe(master_df)