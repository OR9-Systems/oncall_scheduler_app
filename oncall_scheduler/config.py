import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_default_secret_key')

    # Use Docker secrets for sensitive data if available, otherwise fallback to environment variables
    DB_USER = os.environ.get('DB_USER') or open('/run/secrets/db_user', 'r').read().strip()
    DB_PASSWORD = os.environ.get('DB_PASSWORD') or open('/run/secrets/db_password', 'r').read().strip()
    DB_NAME = os.environ.get('DB_NAME') or open('/run/secrets/db_name', 'r').read().strip()
    DB_HOST = os.environ.get('DB_HOST', 'db')

    SQLALCHEMY_DATABASE_URI = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False