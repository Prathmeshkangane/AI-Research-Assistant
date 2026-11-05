import os
import secrets
from urllib.parse import quote_plus
from dotenv import load_dotenv

# override=False: real environment variables (Docker / Render) win over a local .env file.
load_dotenv(override=False)


def _database_uri():
    url = os.getenv("DATABASE_URL")          # lets tests use SQLite and cloud hosts use one URL
    if url:
        return url
    user = os.getenv("DB_USER", "root")
    password = quote_plus(os.getenv("DB_PASSWORD", ""))   # passwords with @ : / # no longer break the URL
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "research_assistant")
    ssl_ca = os.getenv("DB_SSL_CA")           # set only for cloud databases like Aiven
    uri = f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
    return uri + (f"?ssl_ca={ssl_ca}" if ssl_ca else "")


class Config:
    # If SECRET_KEY is missing we generate a random one (sessions reset on restart) instead of crashing.
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}     # survives idle-connection drops on cloud MySQL

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE") == "1"   # set COOKIE_SECURE=1 on https hosts
