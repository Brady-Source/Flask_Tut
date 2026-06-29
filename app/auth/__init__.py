from flask import Blueprint
from authlib.integrations.flask_client import OAuth

auth = Blueprint('auth', __name__)
oauth = OAuth()

from . import views