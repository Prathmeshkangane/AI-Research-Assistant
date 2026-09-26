import os
from dotenv import load_dotenv

load_dotenv()

class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "my_super_secret_key"
    )

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://"
        f"{os.getenv('DB_USER')}:"
        f"{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}/"
        f"{os.getenv('DB_NAME')}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    GEMINI_API_KEY = os.getenv(
        "GEMINI_API_KEY"
    )