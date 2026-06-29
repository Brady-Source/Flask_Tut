import os
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

import sys
import click
from flask_migrate import Migrate, upgrade
from app import create_app, db
from app.models import User, Follower, Role, Permission, Post, Comment, AnonymousUser
from werkzeug.serving import run_simple
from pathlib import Path
from werkzeug.middleware.profiler import ProfilerMiddleware

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)

@app.cli.command()
@click.option('--length', default=20)
def profile(length):
    profile_dir = Path(
        r"C:\Users\dawns\OneDrive\Documents\College\CSCI335 Web Applications Programming\Flask_Tut\profile_dir"
    )
    profile_dir.mkdir(parents=True, exist_ok=True)

    app.wsgi_app = ProfilerMiddleware(
        app.wsgi_app,
        restrictions=[length],
        profile_dir=str(profile_dir)
    )

    run_simple('127.0.0.1', 5000, app, use_debugger=False, use_reloader=False)


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User = User, Role = Role, Post = Post, Comment = Comment, Follower = Follower, Permission = Permission, AnonymousUser = AnonymousUser)

@app.cli.command()
def test():
    """Run the unit tests."""
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)
    
@app.cli.command()
def deploy():
    """Run deployment tasks."""
    # migrate database to latest revision
    upgrade()

    # create or update user roles
    Role.insert_roles()

    # ensure all users are following themselves
    User.add_self_follows()
    
@app.cli.command()
def seed():
    """Load seed data from CSV files."""
    from app.fake import from_csv
    from_csv()