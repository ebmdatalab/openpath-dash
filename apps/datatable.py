import json
from urllib.parse import urlencode

from dash.dependencies import Input, Output

from app import app
from apps.base import humanise_result_filter
from stateful_routing import get_state
from data import get_count_data
import settings


@app.callback(
    [Output("datatable", "data"), Output("datatable", "columns")],
    [
        Input("page-state", "children"),
        Input("datatable", "page_current"),
        Input("datatable", "page_size"),
        Input("datatable", "sort_by"),
    ],
)
def update_datatable(page_state, page_current, page_size, sort_by):
    page_state = get_state(page_state)
    if page_state.get("page_id") != settings.DATATABLE_ID:
        return [], []

    df, columns = get_datatable_with_columns(
        numerators=page_state.get("numerators", []),
        denominators=page_state.get("denominators", []),
        result_filter=page_state.get("result_filter", []),
        ccg_ids_for_practice_filter=page_state.get("ccg_ids_for_practice_filter", []),
        lab_ids_for_practice_filter=page_state.get("lab_ids_for_practice_filter", []),
        by=page_state.get("groupby", None),
        page_current=page_current,
        page_size=page_size,
        sort_by=sort_by,
    )

    return df.to_dict("records"), columns


@app.callback(
    Output("datatable-download-link", "href"),
    [Input("page-state", "children"), Input("datatable", "sort_by")],
)
def update_datatable_download_link(page_state, sort_by):
    page_state = get_state(page_state)
    if page_state.get("page_id") != settings.DATATABLE_ID:
        return "#"

    spec = {
        "numerators": page_state.get("numerators", []),
        "denominators": page_state.get("denominators", []),
        "result_filter": page_state.get("result_filter", []),
        "ccg_ids_for_practice_filter": page_state.get(
            "ccg_ids_for_practice_filter", []
        ),
        "lab_ids_for_practice_filter": page_state.get(
            "lab_ids_for_practice_filter", []
        ),
        "by": page_state.get("groupby", None),
        "sort_by": sort_by,
    }

    query = urlencode({"spec": json.dumps(spec)})
    return f"/download?{query}"


def get_datatable_with_columns(
    page_current=None, page_size=None, sort_by=None, **kwargs
):
    """
    Wrap up `get_count_data` to handle sorting and pagination and various bits
    of reformatting and return dataframe along with column defintions suitable
    for a DataTable view or CSV download.
    """

    df = get_count_data(**kwargs)

    if sort_by:
        df.sort_values(
            [col["column_id"] for col in sort_by],
            ascending=[col["direction"] == "asc" for col in sort_by],
            inplace=True,
        )

    if page_size:
        df = df.iloc[page_current * page_size : (page_current + 1) * page_size]

    if "month" in df.columns:
        df["month"] = df["month"].dt.strftime("%Y-%m-%d")
    if "result_category" in df.columns:
        df["result_category"] = df["result_category"].replace(settings.ERROR_CODES)

    return df, get_columns(df.columns, **kwargs)


def get_columns(
    available_columns,
    numerators=(),
    denominators=(),
    result_filter=None,
    by=None,
    **kwargs,
):
    calc_value_name = "Ratio"
    numerator_name = f"Number of tests ({format_test_codes(numerators)})"

    if denominators == ["per1000"]:
        calc_value_name = "Ratio (x1000)"
        denominator_name = "List size"
    elif denominators == ["raw"]:
        available_columns = [
            c
            for c in available_columns
            if not (c.startswith("denominator") or c.startswith("calc_value"))
        ]
        denominator_name = None
    else:
        if by != "test_code":
            if result_filter and result_filter != "all":
                numerator_name = (
                    f"Number of test results {humanise_result_filter(result_filter)}"
                )
            denominator_name = f"Number of tests ({format_test_codes(denominators)})"
        else:
            if result_filter and result_filter != "all":
                numerator_name = (
                    f"Number of test results {humanise_result_filter(result_filter)}"
                )
                denominator_name = "Number of tests"
            else:
                numerator_name = "Number of tests"
                denominator_name = (
                    f"Number of tests ({format_test_codes(denominators)})"
                )

    columns = [
        {"id": "month", "name": "Month"},
        {"id": "practice_id", "name": "Practice"},
        {"id": "ccg_id", "name": "CCG"},
        {"id": "lab_id", "name": "Lab"},
        {"id": "test_code", "name": "Test code"},
        {"id": "result_category", "name": "Result type"},
        {"id": "numerator", "name": numerator_name},
        {"id": "denominator", "name": denominator_name},
        {"id": "calc_value", "name": calc_value_name},
        {"id": "numerator_error", "name": "Numerator error"},
        {"id": "denominator_error", "name": "Denominator error"},
        {"id": "calc_value_error", "name": "Ratio error"},
    ]

    return [col for col in columns if col["id"] in available_columns]


def format_test_codes(codes):
    if not codes or "all" in codes:
        return "all types"
    else:
        return ", ".join(codes)
