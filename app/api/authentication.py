from flask import g, jsonify
from flask_httpauth import HTTPTokenAuth
from flask_login import login_required, current_user
from . import api
from .errors import unauthorized

token_auth = HTTPTokenAuth(scheme='Bearer')

@token_auth.verify_token
def verify_token(token):
    from ..models import User
    if token:
        user = User.verify_auth_token(token)
        if user:
            g.current_user = user
            return True
        return False

@token_auth.error_handler
def auth_error():
    return unauthorized('Invalid credentials')

@api.route('/tokens', methods=['POST'])
@login_required
def get_token():
    token = current_user.generate_auth_token(expiration=3600)
    return jsonify({'token': token, 'expiration': 3600})