from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///oncall_scheduler.db'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

from oncallapp import routes, models, oncallbackend