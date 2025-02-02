# instance/config.py
class Config:
    SECRET_KEY = 'secret_key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'app/static/uploads'  # Directory where uploaded files will be saved
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Max file size (16MB)
