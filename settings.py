import os
from pathlib import Path

# Error/success codes for `result_category` field
WITHIN_RANGE = 0
UNDER_RANGE = -1
OVER_RANGE = 1
ERR_NO_REF_RANGE = 2
ERR_UNPARSEABLE_RESULT = 3
ERR_INVALID_SEX = 4
ERR_INVALID_RANGE_WITH_DIRECTION = 5
ERR_DISCARDED_AGE = 6
ERR_INVALID_REF_RANGE = 7
ERR_NO_TEST_CODE = 8


# A list of all the charts that appear in the app
CHART_ID = "chart"
DATATABLE_ID = "datatable"
MEASURE_ID = "measure"
PAGES = [CHART_ID, DATATABLE_ID, MEASURE_ID]

# Sparse data filtering
NUM_MONTHS_REQUIRED = 6
NUM_MONTHS_TO_CHECK = 12

# Matplotlib colorscale for heatmaps
COLORSCALE = "viridis"

if "DATA_CSVS_PATH" in os.environ:
    CSV_DIR = Path(os.environ["DATA_CSVS_PATH"])
else:
    CSV_DIR = Path(__file__).parents[0] / "data_csvs"


CACHE_CONFIG = {
    # A simple in-memory cache. This app relies on caching as it assumes it's
    # OK to repeatedly call otherwise expensive functions like `get_data`
    "CACHE_TYPE": "simple",
    # Set to zero to avoid any time-based expiration. Entries will still be
    # evicted once the cache size exceeds the default threshold.
    "CACHE_DEFAULT_TIMEOUT": 0,
}

# This are from the divergent, colourblind-safe "Wong" scheme taken from https://davidmathlogic.com/colorblind/
DECILE_COLOUR = "#56B4E9"
LINE_COLOUR_CYCLE = [
    "#000000",
    "#E69F00",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
]


ERROR_CODES = {
    0: "Within range",
    -1: "Under range",
    1: "Over range",
    2: "No ref range",
    3: "Non-numeric result",
    4: "Unknown sex",
    5: "Insufficient data",
    6: "Underage for ref range",
    7: "Invalid ref range",
}


EMPTY_CHART_LAYOUT = {
    "layout": {
        "xaxis": {"visible": False},
        "yaxis": {"visible": False},
        "annotations": [
            {
                "text": "No matching data",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "font": {"size": 20},
            }
        ],
    }
}


LAB_NAMES = {"cornwall": "Cornwall", "plymouth": "Plymouth", "nd": "N. Devon"}
CORE_DROPDOWN_OPTIONS = [
    {"value": "lab_id", "label": "Lab"},
    {"value": "ccg_id", "label": "CCG"},
    {"value": "practice_id", "label": "Practice"},
]
ANALYSE_DROPDOWN_OPTIONS = CORE_DROPDOWN_OPTIONS + [
    {"value": "test_code", "label": "Test code"},
    {"value": "result_category", "label": "Result type"},
]
