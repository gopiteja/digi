from flask import Flask
from flask_cors import CORS

from app import email_categorization_api

app = Flask(__name__)
CORS(app)