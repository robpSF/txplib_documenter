import streamlit as st
import zipfile
import json
import requests

# Function to list all files in the uploaded .txplib file (zip file)
def list_files_in_zip(zip_file):
    with zipfile.ZipFile(zip_file, 'r') as z:
        return z.namelist()

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

# Function to upload an image to Contentful
def upload_image_to_contentful(image_data):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/entries"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json"
    }
    data = {
        "fields": {
            "assetId": {
                "en-US": image_data["asset_number"]
            },
            "name": {
                "en-US": image_data["asset_number"]
            },
            "tags": {
                "en-US": image_data.get("tags", "")
            },
            "description": {
                "en-US": image_data.get("description", "")
            },
            "url": {
                "en-US": image_data["video_identity"]["url"]
            }
        }
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# Function to upload the .txplib file as an asset in Contentful
def upload_txplib_to_contentful(txplib_file):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json"
    }
    # Create the asset
    asset_data = {
        "fields": {
            "title": {
                "en-US": "Scenario Library"
            },
            "file": {
                "en-US": {
                    "contentType": "application/zip",
                    "fileName": "scenario_library.txplib",
                    "upload": txplib_file
                }
            }
        }
    }
    response = requests.post(url, headers=headers, json=asset_data)
    response.raise_for_status()
    return response.json()

# Function to publish the asset in Contentful
def publish_asset(asset_id):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets/{asset_id}/published"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}"
    }
    response = requests.put(url, headers=headers)
    response.raise_for_status()
    return response.json()

# Function to create a Scenario Library entry in Contentful
def create_scenario_library_entry(asset_id, images_ids):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/entries"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json"
    }
    data = {
        "fields": {
            "name": {
                "en-US": "Scenario Library"
            },
            "description": {
                "en-US": "A scenario library uploaded from Conducttr."
            },
            "file": {
                "en-US": {
                    "sys": {
                        "type": "Link",
                        "linkType": "Asset",
                        "id": asset_id
                    }
                }
            },
            "gallery": {
                "en-US": [{"sys": {"type": "Link", "linkType": "Asset", "id": img_id}} for img_id in images_ids]
            },
            "scenariotype": {
                "en-US": "Facilitated"
            }
        }
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

# Function to handle the upload to Contentful
def upload_to_contentful(txplib_file, selected_images_data):
    # Upload each selected image to Contentful and collect their IDs
    image_ids = []
    for img_data in selected_images_data:
        image_response = upload_image_to_contentful(img_data)
        image_ids.append(image_response["sys"]["id"])
    
    # Upload the .txplib file as an asset in Contentful
    txplib_response = upload_txplib_to_contentful(txplib_file)
    txplib_asset_id = txplib_response["sys"]["id"]
    
    # Publish the .txplib asset
    publish_asset(txplib_asset_id)
    
    # Create a Scenario Library entry and link the uploaded images and txplib asset
    scenario_response = create_scenario_library_entry(txplib_asset_id, image_ids)
    return scenario_response

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
