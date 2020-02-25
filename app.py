import json
import logging
import os

from flask import Flask, render_template, request, abort
from flask_caching import Cache

import dash
import dash_auth
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
server.url_map.strict_slashes = False

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

credentials = os.environ.get("BASIC_AUTH_CREDENTIALS")
if "DEBUG" not in os.environ:
    assert (
        credentials
    ), 'You need to `export BASIC_AUTH_CREDENTIALS="username: password"`'
if credentials:
    username, password = [x.strip() for x in credentials.split(":")]
    auth = dash_auth.BasicAuth(app, {username: password})
    # Reset the static files view to undo the authentication that's been added
    # to it.  Already reported but no sign of it being fixed anytime soon:
    # https://github.com/plotly/dash-auth/issues/57
    app.server.view_functions["static"] = app.server.send_static_file


@server.route("/")
def index():
    return render_template("index.html")


@server.route("/faq")
def faq():
    return render_template("faq.html")


@server.route("/about")
def about():
    return render_template("about.html")


@server.route("/get_involved")
def get_involved():
    return render_template("get_involved.html")


@server.route("/start_here")
def start_here():
    from data import get_org_list

    return render_template(
        "start_here.html", dropdown_options=get_org_list("practice_id")
    )


@server.route("/data_format")
def data_format():
    return render_template("data_format.html")


@server.route("/info_governance")
def info_governance():
    return render_template("info_governance.html")


@server.route("/blog")
def blog_index():
    return render_template("blog.html")


@server.route("/blog/<templatename>")
def blog_page(templatename):
    return render_template("blog/{}.html".format(templatename))


VALID_KEYS = {
    "numerators",
    "denominators",
    "lab_ids_for_practice_filter",
    "ccg_ids_for_practice_filter",
    "result_filter",
    "by",
    "sort_by",
}


@server.route("/download")
def download():
    # Work around circular import
    from apps.datatable import get_datatable_with_columns

    try:
        spec = json.loads(request.args.get("spec"))
    except ValueError:
        abort(400)
    if not spec.keys() <= VALID_KEYS:
        abort(400)
    df, columns = get_datatable_with_columns(**spec)
    headers = {
        "content-type": "text/csv",
        "content-disposition": 'attachment; filename="data.csv"',
    }
    column_headings = [c["name"] for c in columns]
    column_ids = [c["id"] for c in columns]
    csv = df.to_csv(index=False, columns=column_ids, header=column_headings)
    return csv, headers


cache = Cache()
cache.init_app(app.server, config=settings.CACHE_CONFIG)
cache.clear()
