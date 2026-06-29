from flask import request, url_for, jsonify, current_app, g
from . import api
from .errors import forbidden
from .authentication import token_auth

@api.route('/posts/')
@token_auth.login_required
def get_posts():
    from ..models import Post
    from .. import db
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.paginate(
        page=page,
        per_page=current_app.config.get('FLASKY_POSTS_PER_PAGE', 20),
        error_out=False)
    posts = pagination.items
    prev = url_for('api.get_posts', page=page-1) if pagination.has_prev else None
    next = url_for('api.get_posts', page=page+1) if pagination.has_next else None
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev_url': prev,
        'next_url': next,
        'count': pagination.total
    })

@api.route('/posts/<int:id>')
@token_auth.login_required
def get_post(id):
    from ..models import Post
    post = Post.query.get_or_404(id)
    return jsonify(post.to_json())

@api.route('/posts/', methods=['POST'])
@token_auth.login_required
def new_post():
    from ..models import Post, Permission
    from .. import db
    if not g.current_user.can(Permission.WRITE):
        return forbidden('Insufficient permissions')
    post = Post.from_json(request.json)
    post.author = g.current_user
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json()), 201, \
        {'Location': url_for('api.get_post', id=post.id)}

@api.route('/posts/<int:id>', methods=['PUT'])
@token_auth.login_required
def edit_post(id):
    from ..models import Post, Permission
    from .. import db
    post = Post.query.get_or_404(id)
    if g.current_user != post.author and \
            not g.current_user.can(Permission.ADMIN):
        return forbidden('Insufficient permissions')
    post.body = request.json.get('body', post.body)
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json())