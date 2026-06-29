from flask import jsonify
from . import api
from .authentication import token_auth

@api.route('/users/<int:id>', methods=['GET'])
@token_auth.login_required
def get_user(id):
    from ..models import User
    user = User.query.get_or_404(id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role.name if user.role else None
    })