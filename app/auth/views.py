from flask import session, redirect, url_for, flash, render_template, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from . import auth, oauth        
from .. import db
from ..models import User, Role, Comment, Post
from .forms import RegistrationForm, ChangePasswordForm, ChangeEmailForm
from app.email import send_welcome_email
from ..email import send_email
from datetime import datetime, timezone
import os

google = None  # will be set in configure_oauth

def configure_oauth(app):
    global google
    oauth.init_app(app)
    google = oauth.register(
        name='google',
        client_id=os.getenv('FLASK_GOOGLE_CLIENT_ID'),
        client_secret=os.getenv('FLASK_GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

@auth.route('/login/google')
def login_google():
    redirect_uri = url_for('auth.auth_google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@auth.route('/auth/google/callback')
def auth_google_callback():
    try:
        token = google.authorize_access_token()
        userinfo_endpoint = google.server_metadata['userinfo_endpoint']
        resp = google.get(userinfo_endpoint)
        user_info = resp.json()

        email = user_info.get('email')
        name = user_info.get('name')
        sub = user_info.get('id') or user_info.get('sub')

        user = User.query.filter_by(email=email).first()

        is_new_user = False
        if user is None:
            user = User(
                email=email,
                username=name,
                google_id=sub,
                create_at=datetime.now(timezone.utc),
                role_id="3"
            )
            db.session.add(user)
            db.session.commit()
            is_new_user = True

        login_user(user, remember=False)
        session['user_email'] = user.email
        session['user_name'] = user.username

        if is_new_user:
            send_welcome_email(user)

        flash(f'Logged in as {user.username}', 'success')
        return redirect(url_for('main.index'))
    except Exception as e:
        flash(f'Authentication failed: {str(e)}', 'danger')
        return redirect(url_for('auth.login_google'))

@auth.route('/logout')
def logout():
    logout_user()
    session.pop('google_oauth_token', None)
    session.clear()
    response = redirect(url_for('main.index'))
    response.delete_cookie('remember_token')
    flash('You have been logged out.', 'info')
    return response
    
@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You can now login.')
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account',
                   'auth/email/confirm', user=user, token=token)
        flash('A confirmation email has been sent to you by email.')
        return redirect(url_for('main.index'))
    return render_template('auth/register.html', form=form)

@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))

@auth.before_app_request
def before_request():
    if current_user.is_authenticated \
            and not current_user.confirmed \
            and request.blueprint != 'auth' \
            and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))

@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')

@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'Confirm Your Account',
               'auth/email/confirm', user=current_user, token=token)
    flash('A new confirmation email has been sent to you by email.')
    return redirect(url_for('main.index'))

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash('Your password has been updated.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid password.')
    return render_template("auth/change_password.html", form=form)

@auth.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data.lower()
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, 'Confirm your email address',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('An email with instructions to confirm your new email '
                  'address has been sent to you.')
            return redirect(url_for('main.index'))
        else:
            flash('Invalid email or password.')
    return render_template("auth/change_email.html", form=form)