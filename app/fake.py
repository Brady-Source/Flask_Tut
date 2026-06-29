import csv
from sqlalchemy.exc import IntegrityError
from . import db
from .models import User, Post, Comment, Role

def from_csv( comments_file='comments.csv'):
    """Load seed data from CSV files into the database."""
    
    Role.insert_roles()

    # Comments
    with open(comments_file, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            author = User.query.get(int(row['author_id']))
            post = Post.query.get(int(row['post_id']))
            c = Comment(
                body=row['body'],
                body_format=row['body_format'],
                author=author,
                post=post,
                disabled=row['disabled'] == 'True'
            )
            db.session.add(c)
        db.session.commit()

    print("CSV seed data loaded successfully.")