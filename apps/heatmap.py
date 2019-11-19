import logging
import urllib

import plotly.graph_objs as go
from dash.dependencies import Input, Output, State

from app import app
from apps.base import get_chart_title, humanise_entity_name

import numpy as np

import matplotlib

from data import get_count_data
from stateful_routing import get_state
import settings

logger = logging.getLogger(__name__)


def sort_by_index(df):
    """Compute a sort order for the practice charts, based on the mean
    calc_value of the last 6 months.

    Note that we sort in ascending order, because the origin of a
    heatmap is bottom left, and we want the highest values at the top.

    """
    return df.reindex(
        df.fillna(0).iloc[:, -6:].mean(axis=1).sort_values(ascending=True).index, axis=0
    )


def get_colorscale(values, cmap):
    """Given an array of numeric values, return a plotly colorscale for
    the specified matplotlib `cmap` such that the values are
    distributed evenly across all colour values in that cmap.

    """
    num_divisions = 20
    divisions = np.append(np.arange(0, 1, 1 / num_divisions), 1)

    # Generate RGB codes for `num_divisions` equally spaced points
    # across the colormap
    cmap = matplotlib.cm.get_cmap(cmap)
    cmap_points = [list(map(np.uint8, np.array(cmap(x)[:3]) * 255)) for x in divisions]
    cmap_rgb_codes = [f"rgb({x[0]},{x[1]},{x[2]})" for x in cmap_points]

    # Find values at `num_divisions` percentiles, normalised to range 0 - 1
    values = sorted(values[~np.isnan(values)])
    max_value = max(values)
    percentiles = [
        round(x / max_value, 2) for x in np.percentile(values, divisions * 100)
    ]
    # Add a zero value, required by plotly
    scale = [list((0, cmap_rgb_codes[0]))]
    scale.extend([list(a) for a in zip(percentiles, cmap_rgb_codes)])
    return scale


@app.callback(
    Output("heatmap-graph", "figure"),
    [Input("page-state", "children"), Input("url-for-update", "search")],
    [State("deciles-graph", "figure")],
)
def update_heatmap(page_state, current_qs, current_fig):
    EMPTY_RESPONSE = settings.EMPTY_CHART_LAYOUT
    page_state = get_state(page_state)
    if page_state.get("page_id") != settings.CHART_ID:
        return {}
    query_string = urllib.parse.parse_qs(current_qs[1:])
    highlight_entities = set(query_string.get("highlight_entities", []))
    numerators = page_state.get("numerators", [])
    denominators = page_state.get("denominators", [])
    result_filter = page_state.get("result_filter", [])
    groupby = page_state.get("groupby", None)
    practice_filter_entity = page_state.get("practice_filter_entity", None)
    equalise_colorscale = page_state.get("equalise_colorscale", None)
    entity_ids_for_practice_filter = page_state.get(
        "entity_ids_for_practice_filter", []
    )
    col_name = groupby
    trace_df = get_count_data(
        numerators=numerators,
        denominators=denominators,
        result_filter=result_filter,
        practice_filter_entity=practice_filter_entity,
        entity_ids_for_practice_filter=entity_ids_for_practice_filter,
        by=col_name,
        hide_entities_with_sparse_data=page_state.get("sparse_data_toggle"),
    )
    if trace_df.empty:
        return EMPTY_RESPONSE
    vals_by_entity = sort_by_index(
        trace_df.pivot(index=col_name, columns="month", values="calc_value")
    )
    if equalise_colorscale:
        colorscale = get_colorscale(
            vals_by_entity.values.flatten(), settings.COLORSCALE
        )
    else:
        colorscale = settings.COLORSCALE
    # Get labels and order them identically to the values
    labels_by_entity = trace_df.pivot(
        index=col_name, columns="month", values="label"
    ).reindex(vals_by_entity.index)

    entities = [humanise_entity_name(col_name, x) for x in vals_by_entity.index]
    # sort with hottest at top
    trace = go.Heatmap(
        z=vals_by_entity,
        x=vals_by_entity.columns,
        y=entities,
        text=labels_by_entity,
        hoverinfo="text",
        colorscale=colorscale,
    )
    target_rowheight = 20
    height = max(350, target_rowheight * len(entities))
    logger.debug(
        "Target rowheight of {} for {} {}s".format(height, len(entities), groupby)
    )
    if col_name == "practice_id":
        entity_names = ["all practices"]
    elif col_name == "ccg_id":
        entity_names = ["all CCGs"]
    elif col_name == "test_code":
        entity_names = ["all tests"]
    elif col_name == "test_code":
        entity_names = ["all tests"]
    elif col_name == "result_category":
        entity_names = ["all result types"]

    title = get_chart_title(numerators, denominators, result_filter, entity_names)

    def make_highlight_rect(y_index):
        return {
            "layer": "above",
            "xref": "paper",
            "type": "rect",
            "x0": 0,
            "y0": y_index - 0.5,
            "x1": 1,
            "y1": y_index + 0.5,
            "line": {"color": "#d53e4f", "width": 1},
            "fillcolor": "rgba(255, 255, 255, 0.3)",
        }

    highlight_rectangles = [
        make_highlight_rect(vals_by_entity.index.get_loc(x))
        for x in highlight_entities
        if x in vals_by_entity.index
    ]

    return {
        "data": [trace],
        "layout": go.Layout(
            shapes=highlight_rectangles,
            title=title,
            height=height,
            xaxis={"fixedrange": True},
            yaxis={
                "fixedrange": True,
                "automargin": True,
                "tickmode": "array",
                "tickvals": entities,
                "ticktext": entities,
            },
        ),
    }
