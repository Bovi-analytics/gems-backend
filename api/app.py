from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from azure.storage.blob import BlobClient, ContainerClient, BlobServiceClient
from time import sleep
import os
import pandas as pd
from io import BytesIO
from flask_swagger_ui import get_swaggerui_blueprint
from ydata_profiling import ProfileReport
import warnings
import numpy as np
from getpass import getpass
import os
import glob
import pickle
import gdown
from api.functions import *



app = Flask(__name__)
CORS(app)

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Setting up Swagger documentation
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
SWAGGER_URL = "/swagger"
API_URL = "/static/swagger.json"

swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': 'Methane Data API'
    }
)
app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)


# Azure Storage connection string
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
CONTAINER_NAME = "uploads"

# Initialize BlobServiceClient
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)

# Ensure container exists
container_client = blob_service_client.get_container_client(CONTAINER_NAME)
if not container_client.exists():
    container_client.create_container()


@app.errorhandler(404)
def page_not_found(error):
    """return 404 error when a page is not found"""
    return make_response(jsonify({"error": "***Not Found***"}), 404)


@app.route('/')
def index():
    return jsonify({'API Status': 'active'})


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # ✅ Ensure file is an Excel file
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only Excel files (.xls, .xlsx) are allowed.'}), 400

    emails = request.form['emails']
    if emails == '':
        return jsonify({'error': 'No email provided'}), 400
    # print("success")
    # return jsonify({'message': 'File uploaded successfully'})

    try:
        # ===================== Load ground truth data  ===================== #
        container_name = "cornell"
        blob_name = "ground_truth.pkl"

        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        try:
            # Download the blob content as a stream
            download_stream = blob_client.download_blob()
            blob_data = download_stream.readall()  # Read the entire content of the blob
            # Deserialize the pickle content into a Python object
            ground_truth = pickle.loads(blob_data)
        except Exception as e:
            print(f"Failed to read the pickle file from blob storage: {e}")
            return jsonify({'error': f"Failed to read the pickle file from blob storage: {e}"}), 500

        # ===================== Load Excel data from the user into a dataframe ===================== #
        excelData = pd.read_excel(file, sheet_name=None, header=None)

        # delete all the existing html files in the directory.
        delete_html_files_in_dir()
        
        # ===================== Delete all .html files from the "uploads" container ===================== #
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        delete_html_files_in_container(container_client)


        # ===================== RUN ALL CHECKS ===================== #
        output_messages = []  # Mismatches and extra column checks
        output_messages_columns = []  # Column validation (nulls, types, outliers)

        compare_with_ground_truth(ground_truth, excelData, output_messages)
        check_data_beyond_last_variable(excelData, output_messages)

        for sheet_name, df in excelData.items():
            if sheet_name == "ReadMe" or df.empty:
                continue
            output_messages_columns.append(f"\nSheet '{sheet_name}':")  # Include sheet name once
            for col_index, col_name in enumerate(df.columns, start=1):
                col_letter = chr(64 + col_index)
                columnValidation(df[col_name], col_letter, sheet_name, output_messages_columns)

        reports = generate_report_per_sheet(excelData)  # Now returns filenames

        # Upload processed file to Azure Blob Storage
        for report_filename in reports:
            with open(report_filename, "rb") as report_file:
                processed_blob_client = blob_service_client.get_blob_client(
                    container=CONTAINER_NAME, blob=report_filename
                )
                processed_blob_client.upload_blob(report_file.read(), overwrite=True)
                print(f"Uploaded: {report_filename}")
                sleep(2)  # Prevent rate limit issues


        # Generate URL of the processed files folder
        processed_file_url = f"https://methanedata.blob.core.windows.net/{CONTAINER_NAME}"

        # sender_email = os.getenv("EMAIL")
        # app_password = os.getenv("APP_PASSWORD")
        
        recipient_emails = emails.split(',')  # Add your recipients

        send_email_with_reports(
            recipient_emails,
            output_messages, output_messages_columns
        )

        return jsonify(
            {
                'message': 'File processed and uploaded successfully',
                'file_url': processed_file_url
            }
        )
    
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500


@app.route('/get_processed_file', methods=['GET'])
def get_processed_file():
    file_name = request.args.get('file_name')  # Get file name from query parameter

    if not file_name:
        return jsonify({'error': 'Missing file_name parameter'}), 400

    try:
        # Fetch the processed file from Azure Blob Storage
        processed_blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=file_name)

        if not processed_blob_client.exists():
            return jsonify({'error': f'File {file_name} not found in Blob Storage'}), 404

        # Download the file content
        blob_data = processed_blob_client.download_blob().readall()
        
        # Read CSV into Pandas DataFrame
        df = pd.read_csv(BytesIO(blob_data))

        # Convert DataFrame to JSON and return it
        return jsonify({'message': 'File retrieved successfully', 'data': df.to_dict(orient='records')})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/list_files', methods=['GET'])
def list_files():
    try:
        # List blobs in the container
        blob_list = container_client.list_blobs()
        files = [blob.name for blob in blob_list]
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500




if __name__ == '__main__':
    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = os.getenv("API_PORT", 5000)
    # app.run(host=HOST, port=PORT, threaded=True)
    app.run(debug=True)
