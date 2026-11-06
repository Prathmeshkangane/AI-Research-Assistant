from config import Config
from app import app
from models.paper import Paper
from models.user import User

print("DB host:", Config.DB_HOST, "| DB name:", Config.DB_NAME)

with app.app_context():
    print("Papers:", Paper.query.count())
    print("Users:", User.query.count())