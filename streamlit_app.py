import streamlit as st
import zipfile
import json
import pandas as pd
import requests

# Function to extract a specific file from the uploaded .txplib file (zip file)
def extract_file_from_zip(zip_file, target_file_name):
    with zipfile.ZipFile(zip_file, 'r') as z:
        for file_name in z.namelist():
            if target_file_name in file_name:
                with z.open(file_name) as f:
                    return f.read().decode('utf-8')
    return None

# Function to parse JSON structure from the assets.txt content
def parse_assets_json(file_content):
    try:
        data = json.loads(file_content)
        return data
    except json.JSONDecodeError:
        st.error("Failed to decode JSON structure from the file.")
        return None

# Function to display the last five images and allow the user to select three
def display_last_five_images(data):
    if not isinstance(data, list) or len(data) == 0:
        st.error("No image data found in assets.txt.")
        st.write(data)  # Debugging: print out the structure to inspect
        return
    
    # Select the last five images
    last_five_images = data[-5:]
    
    # Display the images and allow the user to select three
    selected_images = st.multiselect(
        "Select up to 3 images:",
        options=[img["asset_number"] for img in last_five_images],
        default=[img["asset_number"] for img in last_five_images[:3]],
        max_selections=3
    )
    
    # Display selected images
    if selected_images:
        st.subheader("Selected Images:")
        for img in last_five_images:
            if img["asset_number"] in selected_images:
                st.image(img["video_identity"]["url"], caption=img["asset_number"])

def main():
    st.title("Txplib File Uploader and Image Selector")
    
    uploaded_file = st.file_uploader("Upload a .txplib file", type="txplib")
    
    if uploaded_file is not None:
        with st.spinner("Extracting and processing file..."):
            # Extract the assets.txt file from the .txplib file
            assets_content = extract_file_from_zip(uploaded_file, "assets.txt")
            if assets_content:
                assets_data = parse_assets_json(assets_content)
                if assets_data:
                    display_last_five_images(assets_data)
            else:
                st.error("Failed to locate 'assets.txt' within the uploaded .txplib file.")

if __name__ == "__main__":
    main()
