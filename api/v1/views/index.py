from api.v1.views import app_views
from flask import jsonify


@app_views.route('/gems/status', methods=['GET'], strict_slashes=False)
def status():
    """return the status of the API"""
    return jsonify({'status': 'active'})


@app_views.route('/', methods=['GET'], strict_slashes=False)
def index():
    """return the status of the API"""
    return jsonify({'message': 'Welcome to the Methane Data API from Bovi-Analytics Lab!'})