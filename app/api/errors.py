from flask import request, render_template, jsonify
from . import api

def forbidden(message):
    response = jsonify({'error': 'forbidden', 'message': message})
    response. status_code = 403
    return response

def unauthorized(message):
    response = jsonify({'error': 'unauthoirzed', 'message': message})
    response.status_code = 401
    return response

api.errorhandler(403)
def forbidden_error(e):
    return forbidden('forbidden')

@api.app_errorhandler(404)
def page_not_found(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return render_template('404.html'), 404

@api.errorhandler(401)
def unauthorized_error(e):
    return unauthorized('unauthorized')