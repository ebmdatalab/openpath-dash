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

Run with `flask get_test_codes` and `flask get_practice_codes`

Then process new data files with `flask process_file <lab_code> <filename>` - this normalises practice codes, test codes, adds error ranges, etc.

Finally run `flask postprocess_files <filenames>` to anonymise (replace practice ids) and report outlier data

## Next steps

Scratchpad:

* Make "all tests" disappear if you select just one. This will require a [custom component](https://github.com/plotly/dash-component-boilerplate) that subclasses [Dropdown](https://github.com/plotly/dash-core-components/blob/dev/src/components/Dropdown.react.js)
* Don't use querystrings for measures text
* Fix chart titles
* Think about suitable warnings for within/outside measures.
  * You want them to have a similar proportion of error rates
  * Some kind of warning when a CCG has lots of errors for a particular test in general

## Data

* In the final ingestion process
  * consider filtering out CCGs with very low totals (i.e. ones not really served by currently ingested labs)
  * consider flagging tests with high ref-range error rates in the test import sheet
  * Note that many reproductive hormone tests have no ref ranges (correctly) for adult women
  * Maybe make a page comparing error codes by test by CCG
* Add ability to annotate charts with "new analyser" or "new ref ranges" events
* Need a "no results" display rather than showing ugly empty chart
* Make datatable toggable on every page
* Allow downloading raw data

## ND
  * Fix ND to output 1-5 suppressed data
  * Fix ND to match up practice codes in advance of main processing
  * Fix ND to drop ZZZ data




## Review my data conversion pipeline
  X Allow it to run incrementally
  * Fix ND not to use pandas
  * Refactor the code to a library
  * Ensure test datasets available for each region so we can run tests
  * Document the expected output format
  X In the ingestion process, add a summary statistics thing to help spot odd tests after we've filtered (ones with lots of errors in particular)


To refactor to library:
 * We need to normalise the reference ranges input format
 * Then we can reuse the lookup functionality
 * Write a function to generate synthetic test data. It just needs month, test_code, source, result_category, sex, age, direction

# Cornwall:

test,min_adult_age,max_adult_age,high_F,high_M,low_F,low_M
125V,0.0,120.0,110.0,110.0,48.0,48.0
17OG,16.0,56.0,31.0,,10.7,
17OG,16.0,120.0,,41.5,,15.0
17OX,16.0,51.0,23.0,,2.5,
17OX,16.0,120.0,,37.0,,8.7
17OX,51.0,120.0,10.9,,0.4,


# Devon:
(no age-based ranges)

test,name,min_adult_age,low_F,low_M,high_F,high_M
ADCA,Calcium (Adjusted),16.0,2.2,2.2,2.6,2.6
AFP3,AFP,18.0,0.0,0.0,6.0,6.0
ALB,Albumin,16.0,35.0,35.0,50.0,50.0
ALKP,Alkaline Phosphatase,16.0,30.0,30.0,130.0,130.0
ALT,ALT,17.0,0.0,0.0,33.0,41.0
AMMO,Ammonia,16.0,11.0,11.0,32.0,32.0
AMY,Amylase,19.0,0.0,0.0,100.0,100.0


1. Generate reference ranges. This will sometimes involve "fixing" them for invalid ref ranges
2. Map rows we're actually interested in at this stage
3. Normalise data - always includes a direction indicator, also converting to floats etc
4. Filter data to GP
5. Output monthly files
6. Combine them





    test    Age     Sex     high    low
656     FSH     4.0     M   0.90    0.00
657     FSH     8.0     F   5.50    0.40
658     FSH     9.0     M   1.60    0.00
659     FSH     10.0    F   4.20    0.40
660     FSH     12.0    M   3.90    0.40
661     FSH     18.0    F   7.80    0.30
662     FSH     18.0    M   5.10    0.80
663     FSH     120.0   M   11.95   0.95
