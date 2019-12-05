"""Get a list of test codes and names that have been mapped between all labs
"""
from flask import Flask

from .get_blogs import get_blogs
from .get_data import get_codes, get_practices, process_file, postprocess_files

app = Flask(__name__)

app.cli.command("get_test_codes")(get_codes)
app.cli.command("get_practices")(get_practices)
app.cli.command("process_file")(process_file)
app.cli.command("postprocess_files")(postprocess_files)


app.cli.command("fetch_blogs")(get_blogs)
