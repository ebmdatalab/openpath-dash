import json
import logging

from flask import Flask, render_template, request, abort
from flask_caching import Cache

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


@server.route("/measures")
def measures():
    return render_template("measures.html")


@server.route("/faq")
def faq():
    return render_template("faq.html")


@server.route("/about")
def about():
    return render_template("about.html")


VALID_KEYS = {
    "numerators",
    "denominators",
    "lab_ids_for_practice_filter",
    "ccg_ids_for_practice_filter",
    "result_filter",
    "sort_by",
}


@server.route("/download")
def download():
    # Work around circular import
    from apps.datatable import get_datatable

    try:
        spec = json.loads(request.args.get("spec"))
    except ValueError:
        abort(400)
    if not spec.keys() <= VALID_KEYS:
        abort(400)
    df = get_datatable(**spec)
    headers = {
        "content-type": "text/csv",
        "content-disposition": 'attachment; filename="data.csv"',
    }
    return df.to_csv(index=False), headers


cache = Cache()
cache.init_app(app.server, config=settings.CACHE_CONFIG)
