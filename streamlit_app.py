import streamlit as st
import zipfile
import json
import requests
import pandas as pd

# Function to list all files in the uploaded .txplib file (zip file)
def list_files_in_zip(zip_file):
    try:
        with zipfile.ZipFile(zip_file) as z:
            return z.namelist()
    except zipfile.BadZipFile:
        st.error("The uploaded file is not a valid zip file.")
        return []

# Function to extract a specific file from the uploaded .txplib file (zip file)
def extract_file_from_zip(zip_file, target_file_name):
    try:
        with zipfile.ZipFile(zip_file, 'r') as z:
            for file_name in z.namelist():
                if target_file_name in file_name:
                    with z.open(file_name) as f:
                        return f.read().decode('utf-8')
    except zipfile.BadZipFile:
        st.error("The uploaded file is not a valid zip file.")
    return None

# Function to parse JSON structure from the assets.txt content
def parse_assets_json(file_content):
    try:
        data = json.loads(file_content)
        return data
    except json.JSONDecodeError:
        st.error("Failed to decode JSON structure from the file.")
        return None

# Function to create a combined table and convert it to a string
def create_combined_table(data):
    # Check if "days" and "tabs" exist in the data
    if "days" not in data or "tabs" not in data:
        st.error("The required 'days' or 'tabs' structures are not found in the file.")
        return None, ""
    
    days = data["days"]
    tabs = data["tabs"]
    
    combined_data = []
    
    for day in days:
        day_name = day.get("name")
        day_id = day.get("id")
        
        for tab in tabs:
            if tab.get("day_id") == day_id:
                tab_name = tab.get("name")
                description = tab.get("serial", {}).get("description", "")
                combined_data.append({"Day": day_name, "Tab Name": tab_name, "Description": description})
    
    if combined_data:
        df = pd.DataFrame(combined_data, columns=["Day", "Tab Name", "Description"])
        df.index = pd.RangeIndex(start=1, stop=len(df) + 1, step=1)  # Reset index and remove number column
        table_string = df.to_string(index=False)  # Convert the DataFrame to a string without index
        return df, table_string
    else:
        return None, "No data available to display."

def main():
    st.title("Txplib File Uploader and Scenario Description")
    
    uploaded_file = st.file_uploader("Upload a .txplib file", type="txplib")
    
    if uploaded_file is not None:
        with st.spinner("Extracting and processing file..."):
            # List all files in the .txplib file
            file_list = list_files_in_zip(uploaded_file)
            
            # Check if the required files exist
            if "design id=2.txt" not in file_list or "assets.txt" not in file_list:
                st.warning("This is an older version of the Conducttr file - please update the editor.")
                return
            
            # Extract the design id=2.txt file and assets.txt from the .txplib file
            design_content = extract_file_from_zip(uploaded_file, "design id=2.txt")
            assets_content = extract_file_from_zip(uploaded_file, "assets.txt")
            
            if design_content and assets_content:
                # Process the design id=2.txt file
                design_data = parse_assets_json(design_content)
                
                # Debug: Print the structure of design_data
                st.write("Design Data:", design_data)
                
                if design_data:
                    df, table_string = create_combined_table(design_data)
                    if df is not None:
                        st.subheader("Scenario Details")
                        st.table(df)  # Display the table
                        
                        # Generate the prompt and send to OpenAI API
                        serial_report = f"Review all the details in this text and write a short 60-word description of the scenario: {table_string}"
                        openai_response = generate_text(serial_report)
                        
                        if openai_response:
                            st.subheader("OpenAI API Response:")
                            st.write(openai_response)
                
                # Process the assets.txt file and display the last five images
                assets_data = parse_assets_json(assets_content)
                selected_images_data = []
                if assets_data:
                    st.subheader("Select Images")
                    selected_images_data = display_last_five_images(assets_data)
                
                # Add a button to upload the data to Contentful
                if st.button("Upload to Contentful?"):
                    if selected_images_data:
                        response = upload_to_contentful(uploaded_file, selected_images_data)
                        st.success("Uploaded successfully to Contentful!")
                        st.write(response)
                    else:
                        st.warning("No images selected for upload.")

if __name__ == "__main__":
    main()
