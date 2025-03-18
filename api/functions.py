from ydata_profiling import ProfileReport
import warnings
import numpy as np
import pandas as pd
import smtplib
import io
import base64
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import smtplib
import glob
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import matplotlib
from azure.storage.blob import BlobServiceClient

matplotlib.use('Agg')




def download_json_from_blob(connection_string, container_name, blob_name):
    """
    Download a JSON file from Azure Blob Storage and return its content as a Python dictionary.
    """
    try:
        # Create the BlobServiceClient object
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Get a client for the container
        container_client = blob_service_client.get_container_client(container_name)
        
        # Get a blob client
        blob_client = container_client.get_blob_client(blob_name)
        
        # Download blob content
        blob_data = blob_client.download_blob()
        json_content = blob_data.readall()

        # Convert JSON content to a Python dictionary
        json_dict = json.loads(json_content)

        print("Token Downloaded successful!")
        return json_dict

    except Exception as e:
        print(f"Error: {e}")
        return None


# function to delete all html files in the upload container
def delete_html_files_in_container(container_client):
    # Get all blobs in the container
    blobs = container_client.list_blobs()
    for blob in blobs:
        if blob.name.endswith(".html"):  # Delete only .html files
            container_client.delete_blob(blob.name)
            print(f"Deleted: {blob.name}")

    print("All .html files in the 'uploads' container have been deleted.")


# function to delete all html files in the directory
def delete_html_files_in_dir():
    html_files = glob.glob("*.html")

    # Remove each .html file
    for file in html_files:
        os.remove(file)
        print(f"Deleted: {file}")

    print("All .html files have been deleted.")


# Functions for Mismatches with Ground Truth
def compare_with_ground_truth(ground_truth, excel_data, output_messages):
    """
    Compare the new Excel data against the saved ground truth for mismatches.
    """
    sheet_names = list(excel_data.keys())[1:]  # Exclude first sheet if it’s a readme sheet
    for sheet in sheet_names:
        if sheet in excel_data:
            new_data_first_four = excel_data[sheet].head(4).reset_index(drop=True)
            if sheet in ground_truth:
                valid_columns = ground_truth[sheet].columns
                extra_columns = list(set(new_data_first_four.columns) - set(valid_columns))

                if extra_columns:
                    extra_data = new_data_first_four[extra_columns]
                    extra_data_mask = extra_data.notna()
                    if extra_data_mask.any().any():
                        output_messages.append(f"\nSheet '{sheet}': Extra data beyond defined columns:\n")
                        for row_idx, col_idx in zip(*np.where(extra_data_mask.values)):
                            col_name = extra_columns[col_idx]
                            output_messages.append(f"  Row {row_idx + 1}, Column '{col_name}'")

                new_data = new_data_first_four[valid_columns]
                ground_truth_data = ground_truth[sheet]
                comparison_mask = (
                    (ground_truth_data.values == new_data.values) |
                    (pd.isna(ground_truth_data.values) & pd.isna(new_data.values))
                )

                if not comparison_mask.all():
                    output_messages.append(f"\nMismatch detected in Sheet '{sheet}':\n")
                    mismatches = np.argwhere(~comparison_mask)
                    for row_idx, col_idx in mismatches:
                        col_name = valid_columns[col_idx]
                        ground_value = ground_truth_data.iloc[row_idx, col_idx]
                        new_value = new_data.iloc[row_idx, col_idx]
                        output_messages.append(f"  Row {row_idx + 1}, Column '{col_name}': Ground truth value = {ground_value}, New dataset value = {new_value}")
            else:
                output_messages.append(f"\nGround truth for sheet '{sheet}' not found!")
        else:
            output_messages.append(f"\nSheet '{sheet}' not found in the new dataset!")



# Function to check for data beyond the last defined variable in row 2
def check_data_beyond_last_variable(excel_data, output_messages):
    """
    Check for data in columns beyond the last defined variable in row 2 for each sheet.
    """
    sheet_names = list(excel_data.keys())[1:]
    for sheet_name in sheet_names:
        sheet_data = excel_data[sheet_name]
        last_defined_col = sheet_data.iloc[2].last_valid_index()
        if last_defined_col is not None:
            data_beyond_last = sheet_data.iloc[:, last_defined_col + 1:].notna().any().any()
            if data_beyond_last:
                output_messages.append(f"\nError: Data found in columns beyond the last defined variable in row 2 in sheet '{sheet_name}'.")



# Functions for Column Validation
def columnNullCheck(TestDataColumn):
    sliced_column = TestDataColumn.iloc[4:]
    return sliced_column[sliced_column.notna()].index.tolist() if sliced_column.notna().any() else []

def columnDataTypeCheck(TestDataColumn):
    sliced_column = TestDataColumn.iloc[4:]
    null_indices = sliced_column[sliced_column.isnull()].index.tolist()
    str_indices = sliced_column[sliced_column.apply(lambda x: isinstance(x, str))].index.tolist()
    numeric_data = sliced_column[sliced_column.apply(lambda x: isinstance(x, (int, float)))]
    return numeric_data, null_indices, str_indices

def columnDataOutliersCheck(numeric_data):
    Q1, Q3 = numeric_data.quantile([0.25, 0.75])
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = numeric_data[(numeric_data < lower_bound) | (numeric_data > upper_bound)]
    zero_positions = numeric_data[numeric_data == 0].index.tolist()
    outliers_info = []
    if not outliers.empty:
        outliers_info.append(f"Outliers at indices: {format_indices(outliers.index.tolist())}")
    if zero_positions:
        outliers_info.append(f"Zero values at indices: {format_indices(zero_positions)}")
    return outliers_info

def format_indices(indices):
    """
    Format a list of indices into a human-readable range format (e.g., 4-39).
    """
    if not indices:
        return ""
    indices.sort()
    ranges = []
    start = indices[0]
    prev = indices[0]

    for i in indices[1:]:
        if i == prev + 1:
            prev = i
        else:
            if start == prev:
                ranges.append(f"{start}")
            else:
                ranges.append(f"{start}-{prev}")
            start = i
            prev = i

    if start == prev:
        ranges.append(f"{start}")
    else:
        ranges.append(f"{start}-{prev}")

    return ", ".join(ranges)

def columnValidation(TestDataColumn, col_letter, sheet_name, output_messages_columns):
    numeric_data, null_indices, str_indices = columnDataTypeCheck(TestDataColumn)

    if null_indices:
        output_messages_columns.append(f"  Column '{col_letter}': Null values at indices {format_indices(null_indices)}")
    if str_indices:
        output_messages_columns.append(f"  Column '{col_letter}': String values at indices {format_indices(str_indices)}")
    if not numeric_data.empty:
        outliers_info = columnDataOutliersCheck(numeric_data)
        if outliers_info:
            for outlier in outliers_info:
                output_messages_columns.append(f"  Column '{col_letter}': {outlier}")



# Function to generate profiling reports
def locate_start_column(df, keyword):
    """
    Locate the row and column where the keyword appears, and select all columns from there.
    """
    for row_index, row in df.iterrows():
        for col_index, value in enumerate(row):
            if str(value) == keyword:
                return row_index, col_index  # Return the row and column index
    return None, None

def locate_last_column(df, row_index, start_col):
    """
    Locate the last column in the specified row where there is an entry.
    """
    for col_index in range(start_col, len(df.columns)):
        if pd.isna(df.iloc[row_index, col_index]):
            return col_index  # Return the column index where entries end
    return len(df.columns)  # If no NaN is found, return the total columns

def process_sheet(df, start_keyword, data_start_row=4):
    """
    Process a sheet to extract relevant columns and rows for profiling.
    """
    # Locate the row and starting column
    start_row, start_col = locate_start_column(df, start_keyword)
    if start_row is None or start_col is None:
        print(f"Keyword '{start_keyword}' not found in sheet. Skipping.")
        return None

    # Find the last column where there is an entry in the located row
    end_col = locate_last_column(df, start_row, start_col)

    # Extract column names from the located row
    column_names = df.iloc[start_row, start_col:end_col].values

    # Extract data starting from the specified row
    data = df.iloc[data_start_row:, start_col:end_col].reset_index(drop=True)
    data.columns = column_names  # Assign column names

    return data


def generate_report_per_sheet(excel_data):
    reports = []  # Store filenames to return

    for sheet_name, df in excel_data.items():
        if sheet_name == "ReadMe" or df.empty:
            continue
        start_keyword = 'researchIdentifier' if sheet_name == 'Animal' else 'animalIdentifier'
        processed_df = process_sheet(df, start_keyword)
        if processed_df is None or processed_df.empty:
            continue

        report_filename = f"{sheet_name}_report.html"
        print("........Before ProfilingReport function.........")
        report = ProfileReport(processed_df, title=f"Profiling Report for {sheet_name}", explorative=True)
        print(".......After ProfilingReport function........")
        report.to_file(report_filename)  # Save to file
        print(".........After to_file function.........")

        reports.append(report_filename)  # Store filename for later use

    return reports  # ✅ Returns list of HTML report filenames


def send_email_with_reports(recipient_emails, output_messages, output_messages_columns, token_json):
    """Sends an email using Gmail API with the provided report."""
    
    def load_credentials():
        # with open("token.json", "r") as token_file:
        #     data = json.load(token_file)
        data = {
        "refresh_token": os.getenv("GMAIL_REFRESH_TOKEN"),
        "client_id": os.getenv("GMAIL_CLIENT_ID"),
        "client_secret": os.getenv("GMAIL_CLIENT_SECRET"),
        "token_uri": os.getenv("GMAIL_TOKEN_URI")
        }
        if None in data.values():
            data = token_json
        creds = Credentials.from_authorized_user_info(info=data)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())  # Automatically refreshes the access token

        return creds
    
    creds = load_credentials()
    service = build("gmail", "v1", credentials=creds) # Authenticate and get Gmail API service
    sender_email = "info@bovi-analytics.com"  # Update this with your email

    subject = "📊 Data Quality & Profiling Report"

    # ✅ **Format `output_messages_columns` into an HTML Table**
    table_rows = ""
    current_sheet = None

    for line in output_messages_columns:
        if line.startswith("\nSheet '"):  
            current_sheet = line.strip("\n:").split()[-1]
        else:
            parts = line.split(": ", 1)
            if len(parts) == 2:
                column, issue = parts
                table_rows += f"<tr><td>{current_sheet}</td><td>{column.strip()}</td><td>{issue.strip()}</td></tr>"

    if not table_rows:
        table_rows = "<tr><td colspan='3' style='text-align:center; color: green;'>✅ No issues found.</td></tr>"

    # ✅ **HTML Email Template with Inline CSS**
    html_body = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                padding: 20px;
            }}
            .container {{
                max-width: 700px;
                background: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
            }}
            h2 {{ color: #333; text-align: center; }}
            p {{ font-size: 14px; line-height: 1.5; color: #555; }}
            .section {{
                background: #f9f9f9;
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 15px;
            }}
            .footer {{ text-align: center; font-size: 12px; color: #888; margin-top: 20px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #007bff; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🔍 Data Validation & Profiling Report</h2>
            <p>Dear Data Provider,</p>
            <p>Thank you for submitting your data for processing. Below, you'll find an automated data quality 
               assessment that includes key insights, validation checks, and profiling reports.</p>

            <div class="section">
                <h3>1️⃣ Mismatches with Ground Truth</h3>
                <p>{''.join(output_messages) if output_messages else "<span style='color: green;'>✅ No mismatches found.</span>"}</p>
            </div>

            <div class="section">
                <h3>2️⃣ Data Quality Checks (Nulls, Data Type, Outliers)</h3>
                <table>
                    <tr>
                        <th>Sheet</th>
                        <th>Column</th>
                        <th>Issue</th>
                    </tr>
                    {table_rows}
                </table>
            </div>

            <div class="section">
                <h3>3️⃣ Comprehensive Data Overview</h3>
                <p>📊 Please see the attached profiling reports for a detailed analysis of your dataset.</p>
            </div>

            <p>Our pipeline is continuously improving with your feedback, ensuring that we maintain high data quality standards.</p>
            <p>Best regards,</p>
            <p><strong>Bovi-Analytics Team</strong></p>
            <div class="footer">📧 This is an automated message. Please do not reply directly.</div>
        </div>
    </body>
    </html>
    """

    # Create email message
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = ", ".join(recipient_emails)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    # Attach generated HTML reports
    report_files = glob.glob("*_report.html")
    for report_file in report_files:
        with open(report_file, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(report_file)}")
            msg.attach(part)

    # Convert email to base64
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        # Send email using Gmail API
        service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
        print("✅ Email sent successfully with attached reports!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")


# def send_email_with_reports(sender_email, app_password, recipient_emails, output_messages, output_messages_columns):
#     """
#     Sends an HTML-styled email with structured tables for readability.
#     """
    
#     # Email subject
#     subject = "📊 Data Quality & Profiling Report"

#     # ✅ **Format `output_messages_columns` into an HTML Table**
#     table_rows = ""
#     current_sheet = None

#     for line in output_messages_columns:
#         if line.startswith("\nSheet '"):  
#             # Extract sheet name correctly
#             current_sheet = line.strip("\n:").split()[-1]
#         else:
#             # Extract column details
#             parts = line.split(": ", 1)
#             if len(parts) == 2:
#                 column, issue = parts
#                 table_rows += f"<tr><td>{current_sheet}</td><td>{column.strip()}</td><td>{issue.strip()}</td></tr>"

#     # If no issues found
#     if not table_rows:
#         table_rows = "<tr><td colspan='3' style='text-align:center; color: green;'>✅ No issues found.</td></tr>"

#     # ✅ **HTML Email Template with Inline CSS**
#     html_body = f"""
#     <html>
#     <head>
#         <style>
#             body {{
#                 font-family: Arial, sans-serif;
#                 background-color: #f4f4f4;
#                 padding: 20px;
#             }}
#             .container {{
#                 max-width: 700px;
#                 background: #fff;
#                 padding: 20px;
#                 border-radius: 8px;
#                 box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
#             }}
#             h2 {{
#                 color: #333;
#                 text-align: center;
#             }}
#             p {{
#                 font-size: 14px;
#                 line-height: 1.5;
#                 color: #555;
#             }}
#             .section {{
#                 background: #f9f9f9;
#                 padding: 10px;
#                 border-radius: 6px;
#                 margin-bottom: 15px;
#             }}
#             .footer {{
#                 text-align: center;
#                 font-size: 12px;
#                 color: #888;
#                 margin-top: 20px;
#             }}
#             table {{
#                 width: 100%;
#                 border-collapse: collapse;
#                 margin-top: 10px;
#             }}
#             th, td {{
#                 border: 1px solid #ddd;
#                 padding: 8px;
#                 text-align: left;
#             }}
#             th {{
#                 background-color: #007bff;
#                 color: white;
#             }}
#             tr:nth-child(even) {{
#                 background-color: #f2f2f2;
#             }}
#         </style>
#     </head>
#     <body>
#         <div class="container">
#             <h2>🔍 Data Validation & Profiling Report</h2>

#             <p>Dear Data Provider,</p>

#             <p>
#                 Thank you for submitting your data for processing. Below, you'll find an automated data quality 
#                 assessment that includes key insights, validation checks, and profiling reports.
#             </p>

#             <div class="section">
#                 <h3>1️⃣ Mismatches with Ground Truth</h3>
#                 <p>{''.join(output_messages) if output_messages else "<span style='color: green;'>✅ No mismatches found.</span>"}</p>
#             </div>

#             <div class="section">
#                 <h3>2️⃣ Data Quality Checks (Nulls, Data Type, Outliers)</h3>
#                 <table>
#                     <tr>
#                         <th>Sheet</th>
#                         <th>Column</th>
#                         <th>Issue</th>
#                     </tr>
#                     {table_rows}
#                 </table>
#             </div>

#             <div class="section">
#                 <h3>3️⃣ Comprehensive Data Overview</h3>
#                 <p>📊 Please see the attached profiling reports for a detailed analysis of your dataset.</p>
#             </div>

#             <p>
#                 Our pipeline is continuously improving with your feedback, ensuring that we maintain high data quality standards.
#                 If you have any questions or feedback, feel free to reach out.
#             </p>

#             <p>Best regards,</p>
#             <p><strong>Bovi-Analytics Team</strong></p>

#             <div class="footer">
#                 📧 This is an automated message. Please do not reply directly.
#             </div>
#         </div>
#     </body>
#     </html>
#     """

#     try:
#         # Initialize email
#         msg = MIMEMultipart()
#         msg['From'] = sender_email
#         msg['To'] = ", ".join(recipient_emails)
#         msg['Subject'] = subject
#         msg.attach(MIMEText(html_body, "html"))  # ✅ Use HTML instead of plain text

#         # Attach generated HTML reports
#         report_files = glob.glob("*_report.html")
#         if report_files:
#             for report_file in report_files:
#                 with open(report_file, "rb") as attachment:
#                     part = MIMEBase("application", "octet-stream")
#                     part.set_payload(attachment.read())
#                     encoders.encode_base64(part)
#                     part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(report_file)}")
#                     msg.attach(part)
#         else:
#             print("⚠ No report files found for attachment.")

#         # Send email
#         smtp_server = "smtp.gmail.com"
#         port = 587
#         with smtplib.SMTP(smtp_server, port) as server:
#             server.starttls()
#             server.login(sender_email, app_password)
#             server.sendmail(sender_email, recipient_emails, msg.as_string())
#             print("✅ Email sent successfully with attached reports!")

#     except Exception as e:
#         print(f"❌ Failed to send email: {e}")
