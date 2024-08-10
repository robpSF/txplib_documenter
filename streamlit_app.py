import streamlit as st
import zipfile
import json
import os
import pandas as pd

def extract_design_id_file(zip_file, target_file_name="design id=2.txt"):
    with zipfile.ZipFile(zip_file, 'r') as z:
        for file_name in z.namelist():
            if target_file_name in file_name:  # Now checking for the correct file name
                with z.open(file_name) as f:
                    return f.read().decode('utf-8')
    return None

def parse_json_structure(file_content):
    try:
        data = json.loads(file_content)
        return data
    except json.JSONDecodeError:
        st.error("Failed to decode JSON structure from the file.")
        return None

def create_day_tab_tables(data):
    if "days" not in data or "tabs" not in data:
        st.error("The required 'days' or 'tabs' structures are not found in the file.")
        return
    
    days = data["days"]
    tabs = data["tabs"]
    
    for day in days:
        day_name = day.get("name")
        day_id = day.get("id")
        
        matching_tabs = []
        for tab in tabs:
            if tab.get("day_id") == day_id:
                tab_name = tab.get("name")
                description = tab.get("serial", {}).get("description", "")
                matching_tabs.append({"name": tab_name, "description": description})
        
        if matching_tabs:
            st.subheader(f"Day: {day_name}")
            df = pd.DataFrame(matching_tabs, columns=["name", "description"])
            st.table(df)
        else:
            st.write(f"No matching tabs found for day: {day_name}")

def main():
    st.title("Txplib File Uploader and Parser")
    
    uploaded_file = st.file_uploader("Upload a .txplib file", type="txplib")
    
    if uploaded_file is not None:
        with st.spinner("Extracting and processing file..."):
            file_content = extract_design_id_file(uploaded_file)
            if file_content:
                data = parse_json_structure(file_content)
                if data:
                    create_day_tab_tables(data)
            else:
                st.error("Failed to locate 'design id=2.txt' within the uploaded .txplib file.")

if __name__ == "__main__":
    main()
