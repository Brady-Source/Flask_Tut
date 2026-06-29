import os
import base64
import json
from email.mime.text import MIMEText
from google.oauth2 import service_account
from googleapiclient.discovery import build
from flask import current_app

def get_gmail_service():
    """Initialize Gmail API service with OAuth credentials from environment."""
    try:
        gmail_service_account = os.getenv('GMAIL_SERVICE_ACCOUNT_EMAIL')
        gmail_private_key = os.getenv('GMAIL_PRIVATE_KEY')

        if not gmail_service_account or not gmail_private_key:
            raise ValueError("Gmail OAuth credentials not configured. Set GMAIL_SERVICE_ACCOUNT_EMAIL and GMAIL_PRIVATE_KEY in .env")

        credentials_dict = {
            "type": "service_account",
            "project_id": "flask-oauth-project",
            "private_key_id": "key-id",
            "private_key": gmail_private_key,
            "client_email": gmail_service_account,
            "client_id": "1234567890",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        }

        credentials = service_account.Credentials.from_service_account_info(
            credentials_dict,
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )

        return build('gmail', 'v1', credentials=credentials)
    except Exception as e:
        current_app.logger.error(f"Failed to initialize Gmail service: {str(e)}")
        return None
    
def send_email(to, subject, template, **kwargs):
    current_app.logger.info(f"send_email called to={to}, subject={subject}, template={template}, kwargs={kwargs}")

def send_welcome_email(user):
    """Send welcome email to new user via Gmail OAuth."""
    try:
        sender_email = os.getenv('GMAIL_SENDER_EMAIL')
        if not sender_email:
            raise ValueError("GMAIL_SENDER_EMAIL not configured in .env")

        service = get_gmail_service()
        if not service:
            current_app.logger.error(f"Could not send email to {user.email}: Gmail service not initialized")
            return "Email service unavailable"

        subject = 'Welcome to Advancing AI'
        body = (
            f"Hi {user.username},\n\n"
            "Welcome to Advancing AI - your social lab notebook for GenAI prompts, "
            "workflows, and experiments.\n\n"
            "You can start by creating your first post or exploring other creators work.\n\n"
            "Happy experimenting!\n"
            "- Advancing AI Team"
        )

        message = MIMEText(body)
        message['to'] = user.email
        message['from'] = sender_email
        message['subject'] = subject

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        send_message = {'raw': raw_message}

        service.users().messages().send(userId='me', body=send_message).execute()
        current_app.logger.info(f"Welcome email sent to {user.email}")
        return "Welcome to Advancing AI!"
    except Exception as e:
        current_app.logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        return f"Error sending email: {str(e)}"
