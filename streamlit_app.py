import streamlit as st
import zipfile
import json
import requests
import pandas as pd
import time

#st.write(st.secrets)

def store_original_txplib_data(txplib_file):
    # Store the original binary data of the file
    original_file_data = txplib_file.read()
    return original_file_data

def store_original_txplib_file(txplib_file):
    # Store the original file object
    return txplib_file

def store_raw_txplib_data(txplib_file):
    # Read and store the raw binary data of the file
    raw_file_data = txplib_file.read()
    return raw_file_data



def check_asset_processing_status(asset_id):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets/{asset_id}"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}"
    }
    response = requests.get(url, headers=headers)
    
    response.raise_for_status()
    asset_details = response.json()
    
    # Check if the asset file is already processed
    file_details = asset_details["fields"]["file"]["en-US"]
    return "url" in file_details  # If 'url' is present, the asset is already processed


def create_image_asset_from_url(image_url, image_name):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json"
    }
    asset_data = {
        "fields": {
            "title": {
                "en-US": image_name
            },
            "file": {
                "en-US": {
                    "fileName": image_name,
                    "contentType": "image/jpeg",  # Adjust content type as needed
                    "url": image_url  # Directly use the provided URL
                }
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=asset_data)
    
    # Log the response for debugging
    st.write("Create Image Asset Response Status Code:", response.status_code)
    #st.write("Create Image Asset Response Content:", response.text)
    
    response.raise_for_status()
    return response.json()["sys"]["id"]  # Return the asset ID


def download_image_from_url(image_url):
    response = requests.get(image_url)
    response.raise_for_status()  # Ensure we got a valid response
    return response.content  # Return the binary content of the image

def upload_image_file_to_contentful(image_binary_data):
    url = f"https://upload.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/uploads"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/octet-stream"
    }
    
    # Upload the binary image data
    response = requests.post(url, headers=headers, data=image_binary_data)
    
    # Log the response for debugging
    st.write("Image File Upload Response Status Code:", response.status_code)
    #st.write("Image File Upload Response Content:", response.text)
    
    # Raise an HTTPError if the response was unsuccessful
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        st.error(f"HTTP error occurred: {e}")
        st.error(f"Response content: {response.text}")
        raise  # Re-raise the exception after logging
    
    return response.json()["sys"]["id"]  # Return the upload ID




def create_image_asset_in_contentful(upload_id, image_name):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json"
    }
    asset_data = {
        "fields": {
            "title": {
                "en-US": image_name
            },
            "file": {
                "en-US": {
                    "fileName": image_name,
                    "contentType": "image/jpeg",  # Adjust content type as needed
                    "uploadFrom": {
                        "sys": {
                            "type": "Link",
                            "linkType": "Upload",
                            "id": upload_id
                        }
                    }
                }
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=asset_data)
    
    # Print the response for debugging
    st.write("Create Image Asset Response Status Code:", response.status_code)
    #st.write("Create Image Asset Response Content:", response.text)
    
    response.raise_for_status()
    return response.json()["sys"]["id"]  # Return the asset ID


def process_and_publish_image_asset(asset_id):
    # Process the asset
    process_asset(asset_id)
    
    # Wait for processing to complete

    time.sleep(5)  # Adjust the time based on the typical processing time
    
    # Publish the asset
    publish_asset(asset_id)




def fetch_asset_latest_version(asset_id):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets/{asset_id}"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}"
    }
    response = requests.get(url, headers=headers)
    
    # Print the response for debugging
    st.write("Fetch Asset Latest Version Status Code:", response.status_code)
    #st.write("Fetch Asset Latest Version Content:", response.text)
    
    response.raise_for_status()
    
    asset_data = response.json()
    return asset_data['sys']['version']


def upload_to_contentful(raw_txplib_data, file_name, selected_images_data, openai_description):
    image_ids = []
    
    # Step 1: Upload each selected image to Contentful and collect their IDs
    for img_data in selected_images_data:
        if "image_file" in img_data:  # Check if it's an uploaded image
            upload_id = upload_image_file_to_contentful(img_data["image_file"].read())
            image_asset_id = create_image_asset_in_contentful(upload_id, img_data["asset_number"])
        else:
            image_binary_data = download_image_from_url(img_data["image_url"])
            upload_id = upload_image_file_to_contentful(image_binary_data)
            image_asset_id = create_image_asset_in_contentful(upload_id, img_data["asset_number"])
        
        process_and_publish_image_asset(image_asset_id)
        image_ids.append(image_asset_id)
    
    # Step 2: Upload the raw .txplib file data as an asset in Contentful
    upload_id = upload_txplib_file_to_contentful(raw_txplib_data, file_name)
    txplib_asset_id = create_txplib_asset_in_contentful(upload_id, file_name)
    
    # Step 3: Process and publish the .txplib asset
    process_and_publish_txplib_asset(txplib_asset_id)
    
    # Step 4: Create a Scenario Library entry using the file name and OpenAI description
    scenario_response = create_scenario_library_entry(txplib_asset_id, image_ids, file_name, openai_description)
    
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
    #st.write("Response Content:", response.text)
    
    # Raise an HTTPError if the response was unsuccessful
    response.raise_for_status()
    
    return response.json()

def upload_txplib_file_to_contentful(raw_file_data, file_name):
    url = f"https://upload.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/uploads"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/octet-stream"
    }
    
    # Upload the raw binary file data
    response = requests.post(url, headers=headers, data=raw_file_data)
    
    # Log the response for debugging
    st.write("File Upload Response Status Code:", response.status_code)
    #st.write("File Upload Response Content:", response.text)
    
    response.raise_for_status()
    return response.json()["sys"]["id"]  # Return the upload ID

def upload_tpp_file_to_contentful(raw_file_data, file_name):
    url = f"https://upload.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/uploads"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/octet-stream"
    }
    
    # Upload the raw binary file data
    response = requests.post(url, headers=headers, data=raw_file_data)
    
    # Log the response for debugging
    st.write("File Upload Response Status Code:", response.status_code)
    #st.write("File Upload Response Content:", response.text)
    
    response.raise_for_status()
    return response.json()["sys"]["id"]  # Return the upload ID

def create_tpp_asset_in_contentful(upload_id, file_name):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json"
    }
    asset_data = {
        "fields": {
            "title": {
                "en-US": file_name
            },
            "file": {
                "en-US": {
                    "fileName": file_name,
                    "contentType": "application/zip",  # Adjust content type if necessary
                    "uploadFrom": {
                        "sys": {
                            "type": "Link",
                            "linkType": "Upload",
                            "id": upload_id
                        }
                    }
                }
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=asset_data)
    
    # Log the response for debugging
    st.write("Create Asset Response Status Code:", response.status_code)
    #st.write("Create Asset Response Content:", response.text)
    
    response.raise_for_status()
    return response.json()["sys"]["id"]  # Return the asset ID


def create_txplib_asset_in_contentful(upload_id, file_name):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json"
    }
    asset_data = {
        "fields": {
            "title": {
                "en-US": file_name
            },
            "file": {
                "en-US": {
                    "fileName": file_name,
                    "contentType": "application/zip",  # Adjust content type if necessary
                    "uploadFrom": {
                        "sys": {
                            "type": "Link",
                            "linkType": "Upload",
                            "id": upload_id
                        }
                    }
                }
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=asset_data)
    
    # Log the response for debugging
    st.write("Create Asset Response Status Code:", response.status_code)
    #st.write("Create Asset Response Content:", response.text)
    
    response.raise_for_status()
    return response.json()["sys"]["id"]  # Return the asset ID

def process_and_publish_txplib_asset(asset_id):
    # Process the asset
    process_asset(asset_id)
    
    # Wait for processing to complete
    time.sleep(5)  # Adjust the time based on the typical processing time
    
    # Publish the asset
    publish_asset(asset_id)


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
    #st.write("File Upload Response Content:", upload_response.text)
    
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
    #st.write("Asset Creation Response Content:", response.text)
    
    response.raise_for_status()
    
    return response.json()


def process_asset(asset_id):
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets/{asset_id}/files/en-US/process"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json"
    }
    response = requests.put(url, headers=headers)
    
    # Log the response status code and content for debugging
    st.write("Process Asset Response Status Code:", response.status_code)
    
    # If the status code indicates no content, skip JSON parsing
    if response.status_code == 204:
        st.write(f"Asset {asset_id} processed successfully. No content returned.")
        return None
    
    try:
        # Attempt to parse the response as JSON if content is expected
        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        st.error(f"JSON decoding error occurred: {e}")
        st.error(f"Response text: {response.text}")
        raise  # Re-raise the exception after logging







# Function to publish the asset in Contentful
def publish_asset(asset_id):
    # Fetch the latest version of the asset
    latest_version = fetch_asset_latest_version(asset_id)
    
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/assets/{asset_id}/published"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "X-Contentful-Version": str(latest_version)  # Use the latest version
    }
    response = requests.put(url, headers=headers)
    
    # Print the response for debugging
    st.write("Publish Asset Response Status Code:", response.status_code)
    #st.write("Publish Asset Response Content:", response.text)
    
    response.raise_for_status()
    
    return response.json()



# Function to create a Scenario Library entry in Contentful
def create_scenario_library_entry(asset_id, image_ids, file_name, openai_description):
    # Truncate the description to 255 characters
    truncated_description = openai_description[:255]
    
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/entries"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json",
        "X-Contentful-Content-Type": "scenarioLibrary"  # Ensure this matches your Contentful content type ID
    }
    data = {
        "fields": {
            "name": {
                "en-US": file_name  # Use the .txplib file name
            },
            "description": {
                "en-US": truncated_description  # Truncated description
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
                "en-US": [{"sys": {"type": "Link", "linkType": "Asset", "id": img_id}} for img_id in image_ids]
            },
            "scenariotype": {
                "en-US": "Facilitated"
            }
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    # Log the response for debugging
    st.write("Create Scenario Library Entry Response Status Code:", response.status_code)
    #st.write("Create Scenario Library Entry Response Content:", response.text)
    
    # Raise an HTTPError if the response was unsuccessful
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
    
    # Allow the user to upload a new image
    uploaded_image = st.file_uploader("Or upload a new image", type=["jpg", "jpeg", "png"])
    
    selected_images_data = []
    
    # Handle the selected images and display them
    for img in last_five_images:
        if img["asset_number"] in selected_images:
            st.image(img["video_identity"]["url"], caption=img["asset_number"], use_column_width=True)
            image_data = {
                "asset_number": img["asset_number"],
                "image_url": img["video_identity"]["url"]  # Assuming the image URL is in video_identity["url"]
            }
            selected_images_data.append(image_data)
    
    # Handle the uploaded image and display it
    if uploaded_image is not None:
        st.image(uploaded_image, caption=uploaded_image.name, use_column_width=True)
        uploaded_image_data = {
            "asset_number": uploaded_image.name,
            "image_file": uploaded_image
        }
        selected_images_data.append(uploaded_image_data)
    
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

# Function to create a Persona Library entry
#def create_persona_library_entry(name, file_id):
#    create_url = f"{base_url}/entries"
#    payload = {
#        "fields": {
#            "name": {"en-US": name},
#            "file": {"en-US": {"sys": {"type": "Link", "linkType": "Asset", "id": file_id}}}
#        }
#    }
#    headers_with_type = headers.copy()
#    headers_with_type["X-Contentful-Content-Type"] = "personaLibrary"
#    response = requests.post(create_url, headers=headers_with_type, json=payload)
#    return response.json()

def create_tpp_library_entry(asset_id, file_name):
    
    url = f"https://api.contentful.com/spaces/{st.secrets['CONTENTFUL_SPACE_ID']}/environments/{st.secrets['CONTENTFUL_ENVIRONMENT']}/entries"
    headers = {
        "Authorization": f"Bearer {st.secrets['CONTENTFUL_ACCESS_TOKEN']}",
        "Content-Type": "application/vnd.contentful.management.v1+json",
        "X-Contentful-Content-Type": "personaLibrary"  # Ensure this matches your Contentful content type ID
    }
    data = {
        "fields": {
            "name": {"en-US": file_name},
            "file": {"en-US": {"sys": {"type": "Link", "linkType": "Asset", "id": asset_id}}}
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    # Log the response for debugging
    st.write("Create Persona Library Entry Response Status Code:", response.status_code)
    #st.write("Create Persona Library Entry Response Content:", response.text)
    
    # Raise an HTTPError if the response was unsuccessful
    response.raise_for_status()
    
    return response.json()



# Streamlit app
st.title("Contentful Library Creator")

# Mode Selection
mode = st.selectbox("Choose Mode", ["Scenario Library", "Persona Library"])    

if mode == "Scenario Library":
    st.header("Upload .TXPLIB file")
    uploaded_file = st.file_uploader("Upload a .txplib file", type="txplib")
    file_name = uploaded_file.name  # Get the .txplib file name
    raw_txplib_data = uploaded_file.read()
    
    if uploaded_file is not None:
        with st.spinner("Extracting and processing file..."):
            # List all files in the .txplib file
            file_list = list_files_in_zip(uploaded_file)
            
            # Check if the required files exist
            #if "design id=2.txt" not in file_list or "assets.txt" not in file_list:
            #    st.warning("This is an older version of the Conducttr file - please update the editor.")
            #    return

            if "design id=2.txt" not in file_list:
                design_file = "design id=1.txt"
            else:
                design_file = "design id=2.txt"
            
            # Extract the design id=2.txt file and assets.txt from the .txplib file
            design_content = extract_file_from_zip(uploaded_file, design_file)
            assets_content = extract_file_from_zip(uploaded_file, "assets.txt")
            
            if design_content and assets_content:
                # Process the design id=2.txt file
                design_data = parse_assets_json(design_content)
                
                # Debug: Print the structure of design_data
                #st.write("Design Data:", design_data)
                
                if design_data:
                    df, table_string = create_combined_table(design_data)
                    if df is not None:
                        st.subheader("Scenario Details")
                        st.table(df)  # Display the table
                        
                        # Generate the prompt and send to OpenAI API
                        serial_report = f"Review all the details in this text and write a short description of the scenario. ##RULES Limit output to 250 characters. Text=: {table_string}"
                        openai_response = generate_text(serial_report)
                        
                        if openai_response:
                            st.subheader("OpenAI API Response:")
                            # Display the response in a text area for editing
                            edited_text = st.text_area("Edit the scenario description:", value=openai_response)
                            
                            # Provide an OK button to proceed with the edited text
                            if st.button("OK"):
                                openai_description = edited_text
                            else:
                                openai_description = openai_response

                
                # Process the assets.txt file and display the last five images
                assets_data = parse_assets_json(assets_content)
                selected_images_data = []
                if assets_data:
                    st.subheader("Select Images")
                    selected_images_data = display_last_five_images(assets_data)
                
                # Add a button to upload the data to Contentful
                if st.button("Upload to Contentful?"):
                    if selected_images_data:
                        response = upload_to_contentful(raw_txplib_data, file_name, selected_images_data, openai_description)
                        st.success("Uploaded successfully to Contentful!")
                        #st.write(response)
                    else:
                        st.warning("No images selected for upload.")

elif mode == "Persona Library":
    st.header("Step 1: Upload .tpp File")
    uploaded_file = st.file_uploader("Choose a .tpp file", accept_multiple_files=False, type=["tpp"])

    if uploaded_file:
        st.write("Uploading .tpp file...")
        file_name = uploaded_file.name
        raw_tpp_data = uploaded_file.read()

        upload_id = upload_tpp_file_to_contentful(raw_tpp_data, file_name)
        tpp_asset_id = create_tpp_asset_in_contentful(upload_id, file_name)

        # Step 3: Process and publish the .tpp asset (should be able to use the existing txplib function
        process_and_publish_txplib_asset(tpp_asset_id)

        # Step 4: Create a Scenario Library entry using the file name and OpenAI description
        #create_response = create_scenario_library_entry(txplib_asset_id, image_ids, file_name, openai_description)
        create_response = create_tpp_library_entry(tpp_asset_id, file_name)
        st.write("Persona Library Entry Created:", create_response)
