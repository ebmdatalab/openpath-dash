import logging

from flask_caching import Cache
from flask import Flask
from flask import render_template

import dash
import dash_bootstrap_components as dbc
import settings
from jinja2 import Environment, FileSystemLoader


logging.basicConfig(
    filename="openpath_dash.log",
    level=logging.DEBUG,
    format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
# set up logging to console
console = logging.StreamHandler()
console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
formatter = logging.Formatter("%(asctime)s : %(levelname)s : %(message)s")
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)

server = Flask(__name__, static_folder="assets")

external_stylesheets = [dbc.themes.BOOTSTRAP]

env = Environment(loader=FileSystemLoader("templates"))
template = env.get_template("base.html")


class DashWithBaseTemplate(dash.Dash):
    def interpolate_index(self, **kwargs):
        return template.render(**kwargs)


app = DashWithBaseTemplate(
    __name__,
    server=server,
    url_base_pathname="/data/",
    external_stylesheets=external_stylesheets,
)
app.static_folder = "assets"


@server.route("/")
def index():
    return render_template("index.html")


cache = Cache()
cache.init_app(app.server, config=settings.CACHE_CONFIG)
