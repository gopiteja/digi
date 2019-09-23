from flask import Flask

from flask_cors import CORS
from flask_caching import Cache
cache = Cache(config={'CACHE_TYPE': 'filesystem', 'CACHE_DIR': '/tmp'})
app = Flask(__name__)
CORS(app)
cache.init_app(app)
# app.config.from_object('config')
from app import queue_api

