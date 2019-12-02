import json
from urllib.parse import urlencode

from dash.dependencies import Input, Output

from app import app
from stateful_routing import get_state
from data import get_count_data
import settings


@app.callback(
    Output("datatable", "data"),
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
        return []

    df = get_datatable(
        numerators=page_state.get("numerators", []),
        denominators=page_state.get("denominators", []),
        result_filter=page_state.get("result_filter", []),
        ccg_ids_for_practice_filter=page_state.get("ccg_ids_for_practice_filter", []),
        lab_ids_for_practice_filter=page_state.get("lab_ids_for_practice_filter", []),
        page_current=page_current,
        page_size=page_size,
        sort_by=sort_by,
    )

    return df.to_dict("records")


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
        "sort_by": sort_by,
    }

    query = urlencode({"spec": json.dumps(spec)})
    return f"/download?{query}"


def get_datatable(page_current=None, page_size=None, sort_by=None, **kwargs):
    """
    Wrap up `get_count_data` to handle sorting and pagination and various bits
    of reformatting
    """
    # By default we want to group by nothing but we need to specify that
    # explictly as by default `get_count_data` will group by `practice_id`
    if "by" not in kwargs:
        kwargs["by"] = None

    df = get_count_data(**kwargs)

    if sort_by:
        df.sort_values(
            [col["column_id"] for col in sort_by],
            ascending=[col["direction"] == "asc" for col in sort_by],
            inplace=True,
        )

    if page_size:
        df = df.iloc[page_current * page_size : (page_current + 1) * page_size]

    df["month"] = df["month"].dt.strftime("%Y-%m-%d")
    df["result_category"] = df["result_category"].replace(settings.ERROR_CODES)

    return df
