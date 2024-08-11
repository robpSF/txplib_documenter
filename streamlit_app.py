import streamlit as st
import zipfile
import json
import requests
import pandas as pd

st.write(st.secrets)


def upload_to_contentful(txplib_file, selected_images_data):
    # Step 1: Upload each selected image to Contentful and collect their IDs
    image_ids = []
    for img_data in selected_images_data:
        image_response = upload_image_to_contentful(img_data)
        image_ids.append(image_response["sys"]["id"])
    
    # Step 2: Upload the .txplib file as an asset in Contentful
    txplib_response = upload_txplib_to_contentful(txplib_file)
    txplib_asset_id = txplib_response["sys"]["id"]
    
    # Step 3: Process the asset to ensure it's ready for publishing
    process_asset(txplib_asset_id)
    
    # (Optional) Wait for a few seconds to allow processing to complete
    import time
    time.sleep(5)
    
    # Step 4: Publish the .txplib asset
    publish_asset(txplib_asset_id)
    
    # Step 5: Create a Scenario Library entry and link the uploaded images and txplib asset
    scenario_response = create_scenario_library_entry(txplib_asset_id, image_ids)
    return scenario_response


# Function to upload an image to Contentful
def upload_image_to_contentful(image_data):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/entries"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json",
        "X-Contentful-Content-Type": "image"  # Specify the content type ID
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
    
    # Print the response for debugging
    st.write("Response Status Code:", response.status_code)
    st.write("Response Content:", response.text)
    
    # Raise an HTTPError if the response was unsuccessful
    response.raise_for_status()
    
    return response.json()



# Function to upload the .txplib file as an asset in Contentful
def upload_txplib_to_contentful(txplib_file):
    # Step 1: Upload the file as a binary file upload
    upload_url = f"https://upload.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/uploads"
    upload_headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/octet-stream"
    }
    
    # Upload the file binary data
    upload_response = requests.post(upload_url, headers=upload_headers, data=txplib_file)
    
    # Print the response for debugging
    st.write("File Upload Response Status Code:", upload_response.status_code)
    st.write("File Upload Response Content:", upload_response.text)
    
    upload_response.raise_for_status()
    upload_data = upload_response.json()

    # Step 2: Create an asset using the uploaded file ID
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json"
    }
    asset_data = {
        "fields": {
            "title": {
                "en-US": "Scenario Library"
            },
            "file": {
                "en-US": {
                    "fileName": "scenario_library.txplib",
                    "contentType": "application/zip",
                    "uploadFrom": {
                        "sys": {
                            "type": "Link",
                            "linkType": "Upload",
                            "id": upload_data["sys"]["id"]
                        }
                    }
                }
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=asset_data)
    
    # Print the response for debugging
    st.write("Asset Creation Response Status Code:", response.status_code)
    st.write("Asset Creation Response Content:", response.text)
    
    response.raise_for_status()
    
    return response.json()


def process_asset(asset_id):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets/{asset_id}/files/en-US/process"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json"
    }
    response = requests.put(url, headers=headers)
    
    # Print the response for debugging
    st.write("Process Asset Response Status Code:", response.status_code)
    
    # Handle the 204 No Content status code without trying to parse JSON
    if response.status_code == 204:
        st.write("Asset processing initiated successfully.")
        return None
    
    # For other successful status codes, we can return the JSON response (if any)
    if response.status_code == 200:
        return response.json()
    
    # Raise an HTTPError if the response was unsuccessful
    response.raise_for_status()




# Function to publish the asset in Contentful
def publish_asset(asset_id):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets/{asset_id}/published"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}"
    }
    response = requests.put(url, headers=headers)
    
    # Print the response for debugging
    st.write("Publish Asset Response Status Code:", response.status_code)
    st.write("Publish Asset Response Content:", response.text)
    
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

# Function to display the last five images and allow the user to select three
def display_last_five_images(data):
    if not isinstance(data, dict) or "list" not in data or len(data["list"]) == 0:
        st.error("No image data found in assets.txt.")
        return []
    
    # Access the list of images
    image_list = data["list"]
    
    # Select the last five images by working backwards
    last_five_images = image_list[-5:]
    
    # Prepare the list of options for the multiselect
    options = [img["asset_number"] for img in last_five_images]
    
    # Allow the user to select images
    selected_images = st.multiselect(
        "Select up to 3 images:",
        options=options,
        default=options[:3],
        max_selections=3
    )
    
    # Return the data for the selected images and display them
    selected_images_data = []
    for img in last_five_images:
        if img["asset_number"] in selected_images:
            st.image(img["video_identity"]["url"], caption=img["asset_number"], use_column_width=True)
            selected_images_data.append(img)
    
    return selected_images_data





# Function to generate text using the OpenAI API
def generate_text(prompt, temp=0.7):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {st.secrets['OPENAI_API_KEY']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temp,
        "max_tokens": 1000,
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0
    }
    response = requests.post(url, headers=headers, json=data)
    #response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

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
