import streamlit as st
import pandas as pd
import os

# --- STYLE INJECTION ---
def apply_custom_style():
    st.markdown("""
        <style>
        /* 1. Main Background and Font */
        .stApp {
            background-color: #fcfcfc;
        }
        
        /* 2. Professional Header Styling */
        h1 {
            color: #002d62 !important; /* NJ Blue */
            font-weight: 800 !important;
            padding-bottom: 20px;
        }
        
        /* 3. Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
            background-color: #ffffff;
            padding: 10px 20px;
            border-radius: 10px 10px 0 0;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }

        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            font-weight: 600 !important;
        }

        /* 4. Table & Dataframe Borders */
        .stTable, .stDataFrame {
            border: 1px solid #e6e9ef;
            border-radius: 8px;
            overflow: hidden;
        }

        /* 5. Custom Sidebar (If you choose to use it later) */
        [data-testid="stSidebar"] {
            background-color: #002d62;
        }
        /* 6. Inactive Tab Text */
        button[data-baseweb="tab"] p {
        font-size: 20px !important;
        font-weight: 600 !important;
        color: #31333F !important;
    }

        /* 7. Active Tab Text (Maroon) */
        button[data-baseweb="tab"][aria-selected="true"] p {
        color: #800000 !important;
    }

        /* 8. The Underline/Highlight Bar (Maroon) */
        /* This targets the move-able bar that follows the active tab */
        div[data-baseweb="tab-highlight"] {
        background-color: #800000 !important;
    }

        /* 9. Removing any remaining default orange borders */
        button[data-baseweb="tab"] {
        border-color: transparent !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Call the function
apply_custom_style()

st.set_page_config(page_title="NJ Library Stats", layout="wide")

@st.cache_data
def load_and_clean_data():
    folder = "data"
    all_files = [f for f in os.listdir(folder) if f.endswith('.xlsx')]
    list_of_dfs = []
    
    for file in all_files:
        path = os.path.join(folder, file)
        temp_df = pd.read_excel(path) 
        
        # 1. Clean headers first
        temp_df.columns = [str(c).strip() for c in temp_df.columns]
        
        # 2. FORCE INSERT THE YEAR AT POSITION 0
        year_val = file.split('.')[0]
        # This makes the year the very first column on the far left
        if 'Data_Year' not in temp_df.columns:
            temp_df.insert(0, 'Data_Year', year_val)
        
        list_of_dfs.append(temp_df)
        
    master = pd.concat(list_of_dfs, ignore_index=True)
    return master

try:
    master_df = load_and_clean_data()
    
    # FIND THE LIBRARY NAME COLUMN
    target_col = next((c for c in master_df.columns if "MUNICIPALITY" in c.upper()), master_df.columns[0])
    
    # --- THE DROPDOWN FIX ---
    # 1. Force names to strings
    master_df[target_col] = master_df[target_col].astype(str).str.strip()
    # 2. Remove any "0" or "nan" entries that shouldn't be names
    master_df = master_df[~master_df[target_col].isin(['0', '0.0', 'nan', 'None'])]
    
    # (Existing County logic...)
    county_col = next((c for c in master_df.columns if "COUNTY" in c.upper() and "CODE" not in c.upper()), None)
    
    # --- TARGETING YOUR SPECIFIC COLUMN ---
    target_col = "Municipality/County"
    
    if target_col not in master_df.columns:
        potential = [c for c in master_df.columns if "Municipality" in c or "Library" in c]
        if potential:
            target_col = potential[0]
        else:
            target_col = master_df.columns[0]

    st.title("📚 NJ Public Library Data Explorer")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Snapshot", "History", "Compare", "Rank", "Data Discovery"])

    with tab1:
        # 1. Selection UI
        c1, c2 = st.columns(2)
        
        raw_lib_list = sorted(master_df[target_col].dropna().unique())
        lib_list = ["Select A Library"] + raw_lib_list
        
        selected_lib = c1.selectbox("Select Municipality", lib_list, key="snap_lib")
        
        year_list = sorted(master_df['Data_Year'].unique(), reverse=True)
        selected_year = c2.selectbox("Select Year", year_list, key="snap_yr")
        
        # --- THE GATEKEEPER ---
        if selected_lib != "Select A Library":
            snap = master_df[(master_df[target_col] == selected_lib) & (master_df['Data_Year'] == selected_year)]
            
            if not snap.empty:
                st.subheader(f"📊 {selected_lib} ({selected_year})")
                
                true_file_path = os.path.join("data", f"{selected_year}.xlsx")
                raw_excel_cols = pd.read_excel(true_file_path, nrows=0).columns.tolist()
                raw_excel_cols = [str(c).strip() for c in raw_excel_cols]
                
                display_df = snap.copy()

                # --- TABLE FORMATTING ---
                for col in display_df.columns:
                    val = display_df[col].values[0]
                    col_upper = str(col).upper()

                    if "ZIP" in col_upper:
                        try:
                            display_df[col] = str(int(float(val))).zfill(5)
                        except:
                            display_df[col] = str(val)
                    elif "COUNTY CODE" in col_upper:
                        try:
                            display_df[col] = str(int(float(val)))
                        except:
                            display_df[col] = str(val)
                    # --- START PERCENTAGE FORMATTING BLOCK ---
                    elif "PERCENTAGE" in col_upper:
                        if pd.isna(val):
                            display_df[col] = "N/A"
                        elif isinstance(val, str) and "%" in val:
                            display_df[col] = val
                        else:
                            try:
                                num_val = float(val)
                                if pd.isna(num_val):
                                    display_df[col] = "N/A"
                                elif num_val == 0:
                                    display_df[col] = "0%"
                                else:
                                    # Calculate raw percentage
                                    p_val = num_val * 100 if 0 < abs(num_val) < 1 else num_val
                                    # Check for whole number (e.g. 5.0 -> 5%)
                                    if round(p_val, 4) % 1 == 0:
                                        display_df[col] = f"{int(round(p_val))}%"
                                    else:
                                        display_df[col] = f"{p_val:.2f}%"
                            except:
                                display_df[col] = str(val) if pd.notnull(val) else "N/A"
                    # --- END PERCENTAGE FORMATTING BLOCK ---
                    else:
                        try:
                            num_val = float(val)
                            display_df[col] = f"{num_val:,.0f}" if not pd.isna(num_val) else "N/A"
                        except:
                            display_df[col] = str(val)

                vertical_df = display_df.T
                vertical_df.columns = ["Value"]

                existing_cols = [c for c in raw_excel_cols if c in vertical_df.index]
                vertical_df = vertical_df.loc[existing_cols]

                vertical_df = vertical_df[
                    ~vertical_df["Value"].astype(str).isin(["N/A", "nan", "None", ""])
                ]

                st.table(vertical_df)
            else:
                st.warning("No data found for this selection.")
        else:
            st.info("👈 Please select a library from the dropdown to view the individual snapshot.")

# --- THE CRITICAL FIX: CLOSE THE TRY BLOCK ---
except Exception as e:
    st.error(f"An error occurred while loading the application: {e}")

# Now, your Tab 2 code can follow safely starting on the next line...

with tab2:
        st.header("📈 Historical Trend Analysis")
        
        # 1. Selection UI
        c1, c2, c3 = st.columns(3)
        
        # LIBRARY SELECTOR
        raw_lib_list = sorted(master_df[target_col].dropna().unique())
        lib_list = ["Select A Library"] + raw_lib_list
        selected_lib_hist = c1.selectbox("Select Library", lib_list, key="hist_lib")
        
        # YEAR SELECTOR
        # We need a fallback list of years if no library is selected yet
        if selected_lib_hist != "Select A Library":
            lib_years = sorted(master_df[master_df[target_col] == selected_lib_hist]['Data_Year'].unique(), reverse=True)
        else:
            lib_years = sorted(master_df['Data_Year'].unique(), reverse=True)
        
        end_year = c2.selectbox("End Year", lib_years, key="hist_end_yr")
        
        # METRIC SELECTOR
        # 1. Create a list of columns
        all_cols = [c for c in master_df.columns if c not in ['Data_Year', target_col]]
        
        # 2. Metric selection (Now starts empty)
        selected_metrics = c3.multiselect(
            "Select Data Points", 
            all_cols, 
            key="hist_metrics",
            placeholder="Choose A Metric" # This will be the only thing visible at first
        )

        # --- THE GATEKEEPER ---
        # Now the gatekeeper only hides the CHART and TABLE
        if selected_lib_hist != "Select A Library":
            
            # 2. Flexible Year Logic
            current_index = lib_years.index(end_year)
            five_years_or_less = lib_years[current_index : current_index + 5]

            # 3. Filter Data
            hist_data = master_df[
                (master_df[target_col] == selected_lib_hist) & 
                (master_df['Data_Year'].isin(five_years_or_less))
            ].copy()

            if not hist_data.empty and len(selected_metrics) > 0:
                # Table Formatting
                table_display = hist_data[['Data_Year'] + selected_metrics].copy()
                
                for col in selected_metrics:
                    if "ZIP" in col.upper():
                        table_display[col] = table_display[col].apply(lambda x: str(int(float(x))).zfill(5) if pd.notnull(x) and x != 0 else "")
                    elif "COUNTY CODE" in col.upper():
                        table_display[col] = table_display[col].apply(lambda x: str(int(float(x))) if pd.notnull(x) and x != 0 else "")
                    else:
                        table_display[col] = pd.to_numeric(table_display[col], errors='coerce')
                        table_display[col] = table_display[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "N/A")

                # Pivot and Reverse Table Order
                hist_pivot = table_display.set_index('Data_Year').T
                chart_matching_order = [y for y in five_years_or_less[::-1] if y in hist_pivot.columns]
                st.table(hist_pivot[chart_matching_order])
                
                st.divider()
                st.subheader("📈 Visual Trends")
                
                # Prepare Chart Data
                chart_df = hist_data[['Data_Year'] + selected_metrics].copy()
                chart_df['Data_Year'] = pd.to_numeric(chart_df['Data_Year'], errors='coerce').astype(int)
                
                clean_name_map = {m: f"Metric_{i+1}" for i, m in enumerate(selected_metrics)}
                display_name_map = {v: k for k, v in clean_name_map.items()}
                chart_df = chart_df.rename(columns=clean_name_map)
                chart_df_melted = chart_df.melt('Data_Year', var_name='Metric', value_name='Value')

                # Create the Chart
                import altair as alt
                line_chart = alt.Chart(chart_df_melted).mark_line(point=True).encode(
                    x=alt.X('Data_Year:O', axis=alt.Axis(title='Year', labelFontSize=14, titleFontSize=16)), 
                    y=alt.Y('Value:Q', axis=alt.Axis(title='Value', labelFontSize=14, titleFontSize=16)),
                    color='Metric:N',
                    tooltip=['Data_Year', 'Metric', 'Value']
                ).properties(width='container', height=400)

                st.altair_chart(line_chart, use_container_width=True)

                # Bold Legend Above Divider
                for clean_name, original_name in display_name_map.items():
                    st.markdown(f"**{clean_name}: {original_name}**")
                
                st.write("---")
        
        else:
            st.info("👈 Please select a library from the dropdown to view historical data.")
with tab3:
        st.header("📊 Library Benchmarking")
        
        # --- 1. IDENTIFY THE ACTUAL COUNTY COLUMN ---
        # We want the one that is definitely the County Name (usually Column J)
        # and NOT the Municipality/Library Name (Column C)
        county_col = None
        for c in master_df.columns:
            c_upper = c.upper()
            # We want 'County' but NOT 'Code', 'Municipality', or 'Library'
            if "COUNTY" in c_upper and "CODE" not in c_upper and "MUNICIPAL" not in c_upper:
                county_col = c
                break
        
        # 2. Selection UI
        c0, c1, c2, c3 = st.columns([1.5, 2.5, 1, 2])
        
        # --- COUNTY FILTER ---
        if county_col:
            # Clean up the list: convert to string, remove 0s/nans, get unique names
            counties = sorted([str(c) for c in master_df[county_col].unique() if pd.notnull(c) and str(c) not in ['0', '0.0', 'nan']])
            
            # CHANGE: We updated the 'key' to be unique
            selected_county = c0.selectbox("Filter by County", ["All Counties"] + counties, key="comp_county_selector")
        else:
            selected_county = "All Counties"
            c0.warning("County Name column not detected.")

        # --- 3. DELIMIT THE LIBRARY LIST ---
        if selected_county != "All Counties":
            # Only show libraries that belong to the chosen county
            filtered_libs = sorted(master_df[master_df[county_col] == selected_county][target_col].dropna().unique())
        else:
            # Show every library in the state
            filtered_libs = sorted(master_df[target_col].dropna().unique())
        
        # Multi-select for libraries (now using the filtered list)
        selected_libs = c1.multiselect("Select Libraries", filtered_libs, key="comp_libs")
        
        # Single Year selection
        year_list_comp = sorted(master_df['Data_Year'].unique(), reverse=True)
        selected_year_comp = c2.selectbox("Select Year", year_list_comp, key="comp_year")
        
        # 1. Create the list of all available metrics
        all_metrics_comp = [c for c in master_df.columns if c not in ['Data_Year', target_col, county_col]]
        
        # 2. Add placeholder to the list
        metric_list_with_placeholder = ["Select A Data Point"] + all_metrics_comp
        
        # 3. Apply to the selectbox
        selected_metric_comp = c3.selectbox(
            "Select Data Point", 
            metric_list_with_placeholder, 
            key="comp_metric"
        )

        # --- 4. DATA FILTERING & SORTING ---
        comp_data = master_df[
            (master_df[target_col].isin(selected_libs)) & 
            (master_df['Data_Year'] == selected_year_comp)
        ].copy()

        if not comp_data.empty and selected_metric_comp != "Select A Data Point":
            # Prepare clean numeric data for the chart
            comp_data[selected_metric_comp] = pd.to_numeric(comp_data[selected_metric_comp], errors='coerce').fillna(0)
            
            # --- BAR CHART ---
            st.subheader(f"📈 {selected_metric_comp} Comparison ({selected_year_comp})")
            
            # We use the same 'Nicknaming' trick to avoid column name errors
            chart_df_comp = comp_data[[target_col, selected_metric_comp]].copy()
            chart_df_comp.columns = ["Library", "Value"]
            
            # Create the Bar Chart
            import altair as alt
            
            bar_chart = alt.Chart(chart_df_comp).mark_bar().encode(
                x=alt.X('Library:N', 
                        sort='-y',
                        axis=alt.Axis(
                            title="Library",
                            labelFontSize=14, 
                            titleFontSize=16,
                            labelAngle=-45  # Tilts names so they don't overlap
                        )),
                y=alt.Y('Value:Q', 
                        axis=alt.Axis(
                            title=selected_metric_comp,
                            labelFontSize=14, 
                            titleFontSize=16
                        )),
                color=alt.Color('Library:N', legend=None),
                tooltip=['Library', 'Value']
            ).properties(width='container', height=400)

            # Display the chart
            st.altair_chart(bar_chart, use_container_width=True)

            # --- DATA TABLE ---
            st.divider()
            st.subheader("📋 Comparison Details")
            
            # 1. Prepare the table data
            table_comp = comp_data[[target_col, selected_metric_comp]].copy()
            
            # 2. THE FIX: Sort descending by the selected metric
            # We do this BEFORE formatting because formatting turns numbers into strings
            table_comp = table_comp.sort_values(by=selected_metric_comp, ascending=False)
            
            # 3. Format the numbers for display (The "Pretty" version)
            if "ZIP" in selected_metric_comp.upper():
                table_comp[selected_metric_comp] = table_comp[selected_metric_comp].apply(
                    lambda x: str(int(float(x))).zfill(5) if x != 0 else ""
                )
            else:
                table_comp[selected_metric_comp] = table_comp[selected_metric_comp].apply(
                    lambda x: f"{x:,.0f}" if pd.notnull(x) else "N/A"
                )

            # 4. Display the table
            st.table(table_comp.set_index(target_col))
            
        else:
            st.info("Please select at least one library to begin the comparison.")

with tab4:
        st.header("🏆 Statewide Ranking")
        st.write("See rankings for public libraries in the state in specific categories.")
        
        c1, c2 = st.columns(2)
        
        # 1. Select the Year
        year_list_lead = sorted(master_df['Data_Year'].unique(), reverse=True)
        selected_year_lead = c1.selectbox("Select Year", year_list_lead, key="lead_year")
        
        # Filter the master data to only this year
        year_specific_data = master_df[master_df['Data_Year'] == selected_year_lead]
        
        # Define columns to exclude
        exclude_cols = ['Data_Year', target_col, county_col]
        
        # --- DELIMIT METRICS BY YEAR & PRESERVE ORDER ---
        available_metrics_this_year = []
        for col in master_df.columns:
            if col not in exclude_cols:
                if col in year_specific_data.columns:
                    series = pd.to_numeric(year_specific_data[col], errors='coerce').fillna(0)
                    if series.sum() > 0:
                        available_metrics_this_year.append(col)
        
        # 2. Select the Metric
        selected_metric_lead = c2.selectbox(
            "Select Metric", 
            ["Select A Metric"] + available_metrics_this_year, 
            key="lead_metric"
        )
        
        if selected_metric_lead != "Select A Metric":
            # 1. Process data: Convert to numeric and filter NULLs/Zeros
            lead_plot_df = year_specific_data[[target_col, selected_metric_lead]].copy()
            lead_plot_df[selected_metric_lead] = pd.to_numeric(lead_plot_df[selected_metric_lead], errors='coerce')
            
            # Remove Nulls and Zeros
            lead_plot_df = lead_plot_df.dropna(subset=[selected_metric_lead])
            lead_plot_df = lead_plot_df[lead_plot_df[selected_metric_lead] > 0]
            
            if not lead_plot_df.empty:
                # 2. Get Top 20
                top_10 = lead_plot_df.nlargest(20, selected_metric_lead)
                top_10.columns = ["Library", "Value"]
                
                # --- CHARTING ---
                import altair as alt
                # Dynamic height so bars look good even if there are only 3 results
                chart_height = max(150, len(top_10) * 45)
                
                chart_lead = alt.Chart(top_10).mark_bar().encode(
                    x=alt.X('Value:Q', title=selected_metric_lead),
                    y=alt.Y('Library:N', sort='-x', title="Library", 
                            axis=alt.Axis(labelFontSize=12, labelLimit=250)),
                    color=alt.Color('Value:Q', scale=alt.Scale(scheme='blues'), legend=None),
                    tooltip=['Library', 'Value']
                ).properties(height=chart_height)

                st.altair_chart(chart_lead, use_container_width=True)

                # --- FORMATTED TABLE ---
                display_table = top_10.copy()
                
                # Apply special formatting for ZIPs/Codes, otherwise use commas
                if "ZIP" in selected_metric_lead.upper() or "CODE" in selected_metric_lead.upper():
                    display_table["Value"] = display_table["Value"].apply(
                        lambda x: str(int(float(x))) if x != 0 else ""
                    )
                else:
                    display_table["Value"] = display_table["Value"].apply(
                        lambda x: f"{x:,.0f}" if pd.notnull(x) else "N/A"
                    )

                display_table.columns = ["Library", selected_metric_lead]
                st.table(display_table.set_index("Library"))
                
            else:
                st.warning(f"No libraries have reported valid data for '{selected_metric_lead}' in {selected_year_lead}.")
        else:
            st.info("Select a metric to see the leaderboard for the chosen year.")

with tab5:
        st.header("🔍 Data Discovery & Export")
        st.write("Search the entire dataset and download your filtered results.")

        # 1. Search Box
        search_query = st.text_input("Search by Library or Municipality Name", placeholder="e.g. 'Ocean', 'Public'...")
        
        # 2. Filter Logic
        if search_query:
            filtered_df = master_df[master_df[target_col].str.contains(search_query, case=False, na=False)].copy()
        else:
            filtered_df = master_df.copy()

        # --- THE AUTO-SORT & ZIP FIX ---
        if not filtered_df.empty:
            # 1. Ensure Year is numeric and sort
            filtered_df['Data_Year'] = pd.to_numeric(filtered_df['Data_Year'], errors='coerce')
            filtered_df = filtered_df.sort_values(by='Data_Year', ascending=False)
            
            # 2. DEFENSIVE ZIP CODE PROTECTION
            def format_zip(val):
                if pd.isna(val) or val == 0 or str(val).strip().lower() in ['0', '0.0', 'nan', 'none', 'unavailable']:
                    return ""
                try:
                    # Strip any .0 if it was loaded as a float, then pad to 5 digits
                    clean_zip = str(int(float(val)))
                    return clean_zip.zfill(5)
                except (ValueError, TypeError):
                    # If it's a word like "Unavailable" or "Pending", just return it as-is
                    return str(val)

            zip_cols = [c for c in filtered_df.columns if "ZIP" in c.upper()]
            for col in zip_cols:
                filtered_df[col] = filtered_df[col].apply(format_zip)

        # --- START PERCENTAGE FORMATTING BLOCK ---
            def format_percentage(val):
                # 1. Check for empty or NaN values
                if pd.isna(val) or str(val).lower() in ['nan', 'none', 'n/a']:
                    return "N/A"
                
                # 2. If it's already a string with a %, leave it alone
                if isinstance(val, str) and "%" in val:
                    return val
                
                try:
                    num_val = float(val)
                    if num_val == 0:
                        return "0%"
                    
                    # 3. Calculate raw percentage value
                    # If decimal < 1 (e.g. 0.05), multiply by 100. Otherwise use as-is.
                    p_val = num_val * 100 if 0 < abs(num_val) < 1 else num_val
                    
                    # 4. The "True Whole Number" Check (Stripping .0)
                    # We round to 4 places to kill float noise, then check if it's an integer
                    if round(p_val, 4) % 1 == 0:
                        return f"{int(round(p_val))}%"
                    else:
                        return f"{p_val:.2f}%"
                except (ValueError, TypeError):
                    # 5. Return text as-is (e.g. "Unavailable")
                    return str(val)

            # Identify and apply to all Percentage columns
            percent_cols = [c for c in filtered_df.columns if "PERCENTAGE" in c.upper()]
            for col in percent_cols:
                filtered_df[col] = filtered_df[col].apply(format_percentage)
        # --- END PERCENTAGE FORMATTING BLOCK ---

        # 3. Display Results
        st.write(f"Found **{len(filtered_df)}** matching records.")
        
        # FIX: Added 'hide_index=True' to remove the row numbers from view
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        # 4. Download Button
        if not filtered_df.empty:
            # FIX: Added 'index=False' to remove row numbers from the actual file
            @st.cache_data
            def convert_df(df):
                return df.to_csv(index=False).encode('utf-8')
            
            csv_data = convert_df(filtered_df)
            
            st.download_button(
                label="📥 Download Filtered Data (CSV)",
                data=csv_data,
                file_name=f"nj_library_export_{search_query if search_query else 'all'}.csv",
                mime="text/csv"
            )

            # --- ABOUT THIS APP MODAL ---
@st.dialog("About This App")
def show_about_page():
    st.write("""
        ### 📚 NJ Public Library Data Explorer
        This application provides a comprehensive look at New Jersey public library statistics. 
       
        It is an experiment is using a vibe coding methodology to develop a data exploration tool 
        web application by Doug Baldwin.

        The entire code base, built in Python, aas well as suggested approach for build tools and web deployment was accomplished 
        with Google Gemini Pro utilizing their Coding partner GEM and human generated prompts. GitHub Codespace
        was used as the IDE for development, testing, and debugging. The application is built with Streamlit
        and deployed on Streamlit Cloud.
             
        The source code for this app can be found on GitHub: https://github.com/dbaldwin1976/nj-lib-stats
        
        The data is sourced from official New Jersey State Library public records, covering multiple years of public library statistics.

        **Data Sources:**
        https://www.njstatelib.org/services_for_libraries/library-development/statistics/
        
        **Features:**
             
        - **Snapshot:** Individual library profiles for specific years.
        - **History:** Multi-year trend analysis with interactive charting.
        - **Benchmarking:** Side-by-side comparison of different municipalities.
        - **Ranking:** Statewide rankings across various metrics.
    """)
    if st.button("Close"):
        st.rerun()

# --- FOOTER WITH MATCHING FONT SIZE ---
st.markdown("---") # Visual separator

# We use columns to center the link or push it to a specific side
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    # We use a button that looks like a link to trigger the About Page
    if st.button("ℹ️ About This App", use_container_width=True):
        show_about_page()

# --- STYLE THE FOOTER BUTTON TO MATCH TAB FONTS ---
st.markdown("""
    <style>
    /* Target the 'About' button specifically */
    div[st-vertical-block] button p {
        font-size: 20px !important;
        font-weight: 600 !important;
        color: #800000 !important;
    }
    </style>
""", unsafe_allow_html=True)