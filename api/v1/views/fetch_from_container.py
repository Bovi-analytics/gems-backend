from api.v1.views import app_views
from flask import jsonify, request, abort, current_app
from azure.storage.blob import BlobServiceClient
from time import sleep
import pandas as pd
import pickle
from io import BytesIO


@app_views.route('/gems/get_processed_file', methods=['GET'], strict_slashes=False)
def get_processed_file():
    file_name = request.args.get('file_name')  # Get file name from query parameter

    if not file_name:
        return jsonify({'error': 'Missing file_name parameter'}), 400

    blob_service_client = current_app.config['blob_service_client']
    CONTAINER_NAME = current_app.config['CONTAINER_NAME']

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


@app_views.route('/gems/list_files', methods=['GET'], strict_slashes=False)
def list_files():
    try:
        # List blobs in the container
        container_client = current_app.config['container_client']
        blob_list = container_client.list_blobs()
        files = [blob.name for blob in blob_list]
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500