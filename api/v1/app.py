from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from azure.storage.blob import BlobServiceClient
from time import sleep
import os
from api.v1.views import app_views
from flask_swagger_ui import get_swaggerui_blueprint


app = Flask(__name__)
app.register_blueprint(app_views)
CORS(app)


# Setting up Swagger documentation
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
SWAGGER_URL = "/api/v1/swagger"
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


# add all initialized variables above to app config
app.config['AZURE_STORAGE_CONNECTION_STRING'] = AZURE_STORAGE_CONNECTION_STRING
app.config['CONTAINER_NAME'] = CONTAINER_NAME
app.config['blob_service_client'] = blob_service_client
app.config['container_client'] = container_client


@app.errorhandler(404)
def page_not_found(error):
    """return 404 error when a page is not found"""
    return make_response(jsonify({"error": "***Not Found***"}), 404)


@app.errorhandler(401)
def not_authorized(error) -> str:
    """ Not authorized handler
    """
    return jsonify({"error": "Unauthorized"}), 401


@app.errorhandler(403)
def forbidden(error) -> str:
    """ Forbidden handler
    """
    return jsonify({"error": "Forbidden"}), 403



if __name__ == '__main__':
    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = os.getenv("API_PORT", 5000)
    # app.run(host=HOST, port=PORT, threaded=True)
    app.run(debug=True)
