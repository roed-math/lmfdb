
from lmfdb.app import app
from flask import Blueprint

drinfeld_page = Blueprint("drinfeld", __name__, template_folder="templates")

from . import main
assert main # silence pyflakes

app.register_blueprint(drinfeld_page, url_prefix="/DrinfeldModule")
