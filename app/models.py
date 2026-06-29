import os
from flask_login import UserMixin, AnonymousUserMixin
from . import login_manager, db
from flask import current_app, request, url_for
from sqlalchemy.sql import func
from itsdangerous import URLSafeTimedSerializer as Serializer
import hashlib
from markdown import markdown
import bleach
from app.exceptions import ValidationError

class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16
    
class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    create_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(64), unique=True)
    permissions = db.Column(db.Integer, default=0)
    default = db.Column(db.Boolean, default=False, index=True)
    users=db.relationship('User', backref='role', lazy='dynamic')
    
    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm
    
    @staticmethod
    def insert_roles():
        roles = {
        'User': [Permission.FOLLOW, Permission.COMMENT],
        'Editor': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
        'Moderator': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE],
        'Admin': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE, Permission.MODERATE, Permission.ADMIN],
        'Applicant User': [Permission.FOLLOW],
        }
        default_role = 'User'
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
                
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, index=True)
    username = db.Column(db.String(32), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), server_default="3")
    name = db.Column(db.String(64))
    email = db.Column(db.String(64), unique=True, index=True)
    age = db.Column(db.Integer)
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text)
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    create_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    last_seen = db.Column(db.DateTime(timezone=True), server_default=func.now())
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    
    
    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()
    
    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            admin_email = current_app.config.get('FLASKY_ADMIN')
            if admin_email and self.email == admin_email:
                self.role = Role.query.filter_by(name='Admin').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()
    
    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(
            follower_id=user.id).first() is not None
    
    def ping(self):
        self.last_seen = func.now()
        db.session.add(self)
        db.session.commit()
    
    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)
    
    confirmed = db.Column(db.Boolean, default=False)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'confirm': self.id})

    def confirm(self, token, expiration=3600):
        s = Serializer (current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expiration)
        except Exception:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True
    
    def generate_reset_token(self, expiration=3600):
        s = Serializer (current_app.config['SECRET_KEY'])
        return s.dumps({'reset': self.id})

    @staticmethod
    def reset_password(token, new_password, expiration=3600):
        s = Serializer (current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expiration)
        except Exception:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True
    
    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer (current_app.config['SECRET_KEY'])
        return s.dumps({'change_email': self.id, 'new_email': new_email})
    
    def change_email(self, token, expiration=3600):
        s = Serializer (current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expiration)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)
        
    def generate_auth_token(self, expiration=3600):
        s = Serializer (current_app.config['SECRET_KEY'])
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token, expiration=3600):
        s = Serializer (current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token, max_age=expiration)
        except Exception:
            return None
        return User.query.get(data['id'])

    def __repr__(self):
        return '<User %r>' % self.username
    
    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id)\
            .filter(Follow.follower_id == self.id)
            
    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'username': self.username,
            'created_at': self.create_at,
            'last_seen': self.last_seen,
            'posts_url': url_for('api.get_user_posts', id=self.id),
            'followed_posts_url': url_for('api.get_user_followed_posts', id=self.id)
        }
    
class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser
    
class Post(db.Model):
    __tablename__='posts'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(64))
    body = db.Column(db.UnicodeText())
    body_html = db.Column(db.UnicodeText())
    body_format = db.Column(db.String(10), default='plain') 
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    category = db.Column(db.String(32))
    sub_category = db.Column(db.String(32))
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    views = db.Column(db.Integer)
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    
    @staticmethod
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'p', 'table', 'thead', 'tbody',
                        'tr', 'th', 'td']
        if target.body_format == 'markdown':
            target.body_html = bleach.linkify(bleach.clean(
                markdown(value, output_format='html'),
                tags=allowed_tags, strip=True))
        elif target.body_format == 'html':
            target.body_html = bleach.linkify(
                bleach.clean(value, tags=allowed_tags, strip=False))
        else:
            target.body_html = None
        
    def to_json(self):
        json_post = {
            'url': url_for('api.get_posts', id=self.id),
            'subject': self.subject,
            'body': self.body,
            'author_id': url_for('api.get_user', id = self.author_id),
            'categrory': self.category,
            'sub_category': self.sub_category,
            'timestamp': self.timestamp,
            'views': self.views,
            'comments_url': url_for('api.get_post_comments', id = self.id),
            'comment_count': self.comments.count()
        }
        return json_post
    
    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)

db.event.listen(Post.body, 'set', Post.on_changed_body)
    
class Comment(db.Model):
    __tablename__='comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(180))
    body_html = db.Column(db.Text)
    body_format = db.Column(db.String(10), default='plain')
    timestamp = db.Column(db.DateTime(timezone=True), server_default=func.now())
    disabled = db.Column(db.Boolean, default=False)
    author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer,db.ForeignKey('posts.id'))
    
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        if target.body_format == 'markdown':
            allowed_tags = ['a', 'abbr', 'b', 'blockquote', 'code',
                            'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul', 'p']
            target.body_html = bleach.linkify(bleach.clean(
                markdown(value, output_format='html'),
                tags=allowed_tags, strip=True))
        else:
            target.body_html = bleach.linkify(bleach.clean(value))

db.event.listen(Comment.body, 'set', Comment.on_changed_body)
    
class Follower(db.Model):
    __tablename__='followers'
    follower_id = db.Column(db.Integer, primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'))