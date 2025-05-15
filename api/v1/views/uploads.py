from api.v1.views import app_views
from flask import jsonify, request, Response, render_template_string
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
from authlib.integrations.flask_oauth2 import ResourceProtector
from api.v1.views.validator import Auth0JWTBearerTokenValidator
import os

require_auth = ResourceProtector()
validator = Auth0JWTBearerTokenValidator(
    'dev-1bd3bttgj2px61zz.us.auth0.com',
    'https://gems.bovi-analytics.com/'
)
require_auth.register_token_validator(validator)

ALLOWED_EXTENSIONS = {'xls', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Sample data (unchanged)
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

# HTML template (unchanged)
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
@app_views.route('/gems/me', methods=['GET'])
@require_auth()
def get_user_info():
    token = request.headers.get("Authorization").split("Bearer ")[1]
    # roles = extract_roles_from_token(token)
    return jsonify({
        "message": "Authenticated!"
        # "roles": roles
    })

@app_views.route('/gems/upload', methods=['POST'], strict_slashes=False)
@require_auth()
def upload():
    """Upload a file and process it"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only Excel files (.xls, .xlsx) are allowed.'}), 400

    emails = request.form.get('emails', '')
    if not emails:
        return jsonify({'error': 'No email provided'}), 400

    # return jsonify({'message': 'File upload successful'}), 200
    try:
        # Load ground truth data
        container_name = "cornell"
        blob_name = "ground_truth.pkl"
        AZURE_STORAGE_CONNECTION_STRING = current_app.config['AZURE_STORAGE_CONNECTION_STRING']
        CONTAINER_NAME = current_app.config['CONTAINER_NAME']

        blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        try:
            download_stream = blob_client.download_blob()
            blob_data = download_stream.readall()
            ground_truth = pickle.loads(blob_data)
        except Exception as e:
            print(f"Failed to read the pickle file from blob storage: {e}")
            return jsonify({'error': f"Failed to read the pickle file from blob storage: {e}"}), 500

        # Load Excel data
        excelData = pd.read_excel(file, sheet_name=None, header=None)

        # Delete existing HTML files
        delete_html_files_in_dir()
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        delete_html_files_in_container(container_client)

        # Run checks
        output_messages = []
        output_messages_columns = []
        compare_with_ground_truth(ground_truth, excelData, output_messages)
        check_data_beyond_last_variable(excelData, output_messages)

        for sheet_name, df in excelData.items():
            if sheet_name == "ReadMe" or df.empty:
                continue
            output_messages_columns.append(f"\nSheet '{sheet_name}':")
            for col_index, col_name in enumerate(df.columns, start=1):
                col_letter = chr(64 + col_index)
                columnValidation(df[col_name], col_letter, sheet_name, output_messages_columns)

        reports = generate_report_per_sheet(excelData)

        # Upload reports to Azure
        for report_filename in reports:
            with open(report_filename, "rb") as report_file:
                processed_blob_client = blob_service_client.get_blob_client(
                    container=CONTAINER_NAME, blob=report_filename
                )
                processed_blob_client.upload_blob(report_file.read(), overwrite=True)
                print(f"Uploaded: {report_filename}")
                sleep(2)

        processed_file_url = f"https://methanedata.blob.core.windows.net/{CONTAINER_NAME}"
        recipient_emails = [email.strip() for email in emails.split(',') if email.strip()]
        if not recipient_emails:
            return jsonify({'error': 'No valid emails provided'}), 400

        token_js = download_json_from_blob(AZURE_STORAGE_CONNECTION_STRING, CONTAINER_NAME, "token.json")
        sleep(2)
        # Uncomment to enable email sending
        # send_email_with_reports(recipient_emails, output_messages, output_messages_columns, token_js)

        return jsonify({
            'message': 'File processed and uploaded successfully',
            'file_url': processed_file_url
        }), 200

    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

@app_views.route('/animal.<file_format>')
def get_animal(file_format):
    """Return sample animal data in various formats"""
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