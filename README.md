# Deployment

Via `dokku`. Add a remote called `dokku` that points to `dokku@dokku.ebmdatalab.net:openpath-flask`.

Then you can do `git push dokku master` to deploy, assuming your ssh public key is installed for the `dokku` user on that server.

Deployment requires a username and password to be set in the environment. You can do this on the server thus:


    dokku config:set openpath-flask BASIC_AUTH_CREDENTIALS="username: password"

# Persistent storage

The raw data is currently not checked into the repo, pending a decision on doing so.

Until that decision, data can be made available to the app via dokku's Persistent Storage

    dokku storage:mount openpath-flask /var/lib/dokku/data/storage/openpath-dash/data_csvs:/var/data_csvs
    dokku config:set openpath-flask DATA_CSVS_PATH=/var/data_csvs


To update the data, you'll want to update it in `/var/lib/dokku/data/storage/openpath-dash/data_csvs`.  This should contain a copy of everything in `data_csvs/` from the repo, plus any newer `all_processed.csv.zip` file.

You must redeploy (restart) an app to mount or unmount to an existing app's container.

# Navigating the code

* This is a Dash app. Pretty much all the Dash documentation is in the [short tutorial](https://dash.plot.ly/getting-started). This is worth reading in full before getting started.  The docstrings in the code (linke from that documentation) are very thorough.
* Dash is a Flask app that wraps React + Plotly. It runs as a single page app.
* All the charts are Plotly charts, whose best reference is [here](https://plot.ly/python/reference/), although you have to work out how to invoke them in a Dash-like way yourself.


To run the app, run `python index.py`. This sets up a flask app (`app.py`), and imports modules in `apps/`, each providing a particular chart for the single page app.

Per-client state is stored as stringified JSON in a hidden div. Bookmarkable state is mirrored in the location bar of the browser.  This is all handled by `apps/stateful_routing.py`.

When a chart element (defined in `layouts.py` changes, its state flows to the `stateful_routing` module and the location bar; the various charts are wired to changes in the per-client state and update accordingly. Charts that are not currently being viewed are hidden (see `apps/base.py`), as Dash requires everything wired up for callbacks to be present on the page.

# Is Dash a good choice?

Probably, enough to give it a proper change.

Benefits:

* Very expressive, terse code
* Plotly charts feel nicer than Highcharts. It is easier to get data in the right format and finding the options we want to use is easier

Costs:

* Not a full framework: have had to handle URL / state / multipage stuff ourselves (see `stateful_routing.py`)

## Performance

Displaying 86 charts on a fast laptop takes around 15s. This time is
halved if you remove all interactivity from the charts.

There may be further performance improvements from selectively removing interactivity.

There also seems to be an opportunity to cut down the time inside plotly-py; 25% of the time is spent in a string validator ([look at this as HTML in a browser](https://gist.github.com/sebbacon/00dbf2c3b1cd25b6762d003806cb8f2e))

Currently the same thing takes about 45s on OpenPrescribing, though
probably 40s of this is network time; the main concern with Dash here
is that it chews a lot of CPU. We would probably want to implement a
smooth-scroll handler for this, per [these notes](https://community.plot.ly/t/scroll-position/4618)

# Pipeline

Run with `flask get_practice_codes` gets practice codes (crucially, including CCG membership)


Then process new data files with `flask process_file <lab_code> <filename>` -  this

* normalises practice codes (i.e. ensures they're all ODS codes)
* adds a lab code column to each CSV
* outputs a summary table of possibly-interesting outlier tests (e.g. ones that don't have reference ranges, etc)
* trims the data with respect to lead-in data (the first months supplied with include tests requested some time before)
* excludes practices we don't know about (based on data in OP) and practices for which we don't have list size data
* removes extreme outlier practices (ones with fewer than 1000 tests)
* combines everything into one big file


Finally run `flask postprocess_files <filenames>` to anonymise (replace practice ids) and report outlier data
