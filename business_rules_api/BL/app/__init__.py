from flask import Flask

from flask_cors import CORS
app = Flask(__name__)
CORS(app)
# app.config.from_object('config')
from app import business_rules_api

