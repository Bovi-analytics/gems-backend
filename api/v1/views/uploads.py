from api.v1.views import app_views
from flask import jsonify, request, abort, current_app, Response, render_template_string
import csv
import io
from azure.storage.blob import BlobServiceClient
from time import sleep
import pandas as pd
import pickle
from api.v1.functions import (
    compare_with_ground_truth,
    check_data_beyond_last_variable,
    columnValidation,
    generate_report_per_sheet,
    delete_html_files_in_dir,
    delete_html_files_in_container,
    download_json_from_blob,
    send_email_with_reports
)
# from api.v1.views.auth import requires_auth
from authlib.integrations.flask_oauth2 import ResourceProtector
from api.v1.views.validator import Auth0JWTBearerTokenValidator
import os
import requests
from jose import jwt


require_auth = ResourceProtector()
validator = Auth0JWTBearerTokenValidator(
                'dev-mvz0o2d83zbkctso.us.auth0.com',
                "https://gems-backend.bovi-analytics.com"
                # 'https://dev-mvz0o2d83zbkctso.us.auth0.com/api/v2/'
            )
require_auth.register_token_validator(validator)
# print(require_auth)
data = [
    {"animal": "Holstein Cow", "category": "Dairy", "methane_emission_kg_per_day": 0.35, "milk_production_liters_per_day": 28},
    {"animal": "Jersey Cow", "category": "Dairy", "methane_emission_kg_per_day": 0.30, "milk_production_liters_per_day": 22},
    {"animal": "Guernsey Cow", "category": "Dairy", "methane_emission_kg_per_day": 0.33, "milk_production_liters_per_day": 25},
    {"animal": "Buffalo", "category": "Dairy", "methane_emission_kg_per_day": 0.38, "milk_production_liters_per_day": 20},
    {"animal": "Goat", "category": "Dairy", "methane_emission_kg_per_day": 0.07, "milk_production_liters_per_day": 2.5},
    {"animal": "Sheep", "category": "Dairy", "methane_emission_kg_per_day": 0.06, "milk_production_liters_per_day": 1.8},
    {"animal": "Zebu", "category": "Dairy", "methane_emission_kg_per_day": 0.32, "milk_production_liters_per_day": 15},
    {"animal": "Yak", "category": "Dairy", "methane_emission_kg_per_day": 0.29, "milk_production_liters_per_day": 5},
    {"animal": "Camel", "category": "Dairy", "methane_emission_kg_per_day": 0.21, "milk_production_liters_per_day": 6},
    {"animal": "Reindeer", "category": "Dairy", "methane_emission_kg_per_day": 0.11, "milk_production_liters_per_day": 1}
]


# HTML template for the table
html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Animal Table</title>
    <style>
        table {
            border-collapse: collapse;
            width: 50%;
            margin: 40px auto;
            font-family: Arial, sans-serif;
        }
        th, td {
            padding: 10px;
            border: 1px solid #ccc;
            text-align: left;
        }
        th {
            background-color: #f4f4f4;
        }
        caption {
            caption-side: top;
            font-size: 24px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <table>
        <caption>Animal List</caption>
        <thead>
            <tr>
                {% for key in data[0].keys() %}
                <th>{{ key.capitalize() }}</th>
                {% endfor %}
            </tr>
        </thead>
        <tbody>
            {% for item in data %}
            <tr>
                {% for value in item.values() %}
                <td>{{ value }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", 'dev-mvz0o2d83zbkctso.us.auth0.com')
API_IDENTIFIER = os.getenv("API_IDENTIFIER", "https://gems-backend.bovi-analytics.com")
ALGORITHMS = os.getenv("ALGORITHMS", "RS256").split(",") 


ALLOWED_EXTENSIONS = {'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app_views.route('/gems/upload', methods=['POST'], strict_slashes=False)
@require_auth()
def upload():
    """Upload a file and process it"""
    return jsonify({"message": "Upload endpoint"})
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    return jsonify({'message': 'File uploaded successfully'})
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

        AZURE_STORAGE_CONNECTION_STRING = current_app.config['AZURE_STORAGE_CONNECTION_STRING']
        CONTAINER_NAME = current_app.config['CONTAINER_NAME']

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

        token_js = download_json_from_blob(AZURE_STORAGE_CONNECTION_STRING, CONTAINER_NAME, "token.json")
        sleep(2)
        # send_email_with_reports(
        #     recipient_emails,
        #     output_messages, output_messages_columns, token_js
        # )

        return jsonify(
            {
                'message': 'File processed and uploaded successfully',
                'file_url': processed_file_url
            }
        )
    
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500


@app_views.route("/token", methods=["POST"])
def get_token():
    url = "https://dev-mvz0o2d83zbkctso.us.auth0.com/oauth/token"
    payload = {
        "client_id": "IdXcyXJ6cazC4A2tL29nuReMXMFbM2Jg",
        "client_secret": "HQJ9wu3WbW6HMqX_EzfK0VlNblPWsmILGl_uh_mGCs9MY6REazpSm7UlGh6MfLp9",
        "audience": "https://gems-backend.bovi-analytics.com",
        "grant_type": "client_credentials"
    }
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, headers=headers)
    print(response.json())
    return jsonify(response.json())



@app_views.route('/animal.<file_format>')
# @require_auth()
def get_animal(file_format):
    if file_format == 'json':
        return jsonify(data)

    elif file_format == 'csv':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return Response(output.getvalue(), mimetype='text/plain')

    elif file_format == 'xml':
        xml_data = "<animals>"
        for item in data:
            xml_data += "<animal>"
            for key, value in item.items():
                xml_data += f"<{key}>{value}</{key}>"
            xml_data += "</animal>"
        xml_data += "</animals>"
        return Response(xml_data, mimetype='application/xml')

    elif file_format == 'html':
        rendered_html = render_template_string(html_template, data=data)
        return Response(rendered_html, mimetype='text/html')

    else:
        return jsonify({"error": "Unsupported format"}), 400