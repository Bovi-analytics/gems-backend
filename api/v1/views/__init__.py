from flask import Blueprint


app_views = Blueprint('app_views', __name__, url_prefix='/api/v1')

from api.v1.views.index import *
from api.v1.views.fetch_from_container import *
from api.v1.views.uploads import *
from api.v1.views.chatbot import *