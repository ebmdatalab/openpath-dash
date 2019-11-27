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

    numerators = page_state.get("numerators", [])
    denominators = page_state.get("denominators", [])
    result_filter = page_state.get("result_filter", [])
    practice_filter_entity = page_state.get("practice_filter_entity", None)
    entity_ids_for_practice_filter = page_state.get(
        "entity_ids_for_practice_filter", []
    )

    df = get_count_data(
        numerators=numerators,
        denominators=denominators,
        by=None,
        practice_filter_entity=practice_filter_entity,
        entity_ids_for_practice_filter=entity_ids_for_practice_filter,
        result_filter=result_filter,
    )

    # Sort and paginate
    if sort_by:
        df.sort_values(
            [col["column_id"] for col in sort_by],
            ascending=[col["direction"] == "asc" for col in sort_by],
            inplace=True,
        )
    df = df.iloc[page_current * page_size : (page_current + 1) * page_size]
    # XXX make downloadable:
    # https://github.com/plotly/dash-core-components/issues/216 -
    # perhaps
    # https://community.plot.ly/t/allowing-users-to-download-csv-on-click/5550/9
    # XXX possibly remove this
    df["month"] = df["month"].dt.strftime("%Y-%m-%d")
    df["result_category"] = df["result_category"].replace(settings.ERROR_CODES)
    return df.to_dict("records")
