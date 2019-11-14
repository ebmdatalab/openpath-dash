import logging
import urllib

import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State

import numpy as np
from app import app
from apps.base import get_sorted_group_keys
from apps.base import get_chart_title
from data import get_count_data
from stateful_routing import get_state
import settings


logger = logging.getLogger(__name__)


def get_practice_deciles(df):
    """Compute deciles across `calc_value` over `practice_id` for each month.

    Returns a list of (decile, value) tuples (e.g. (10, 4.223))
    """
    deciles = np.array(range(10, 100, 10))
    vals_by_practice = df.pivot(columns="month", values="calc_value")
    deciles_data = np.nanpercentile(vals_by_practice, axis=0, q=deciles)
    return zip(deciles, deciles_data)


def get_practice_decile_traces(df):
    """Return a set of `Scatter` traces  suitable for adding to a Dash figure
    """
    deciles_traces = []
    months = pd.to_datetime(df["month"].unique())
    for n, decile in get_practice_deciles(df):
        if n == 50:
            style = "dash"
        else:
            style = "dot"
        deciles_traces.append(
            go.Scatter(
                x=months,
                y=decile,
                name="{}th".format(n),
                line=dict(color="blue", width=1, dash=style),
                hoverinfo="skip",
            )
        )
    return deciles_traces


@app.callback(
    [Output("deciles-graph", "figure"), Output("url-for-update", "search")],
    [Input("page-state", "children"), Input("heatmap-graph", "clickData")],
    [State("url-for-update", "search")],
)
def update_deciles(page_state, click_data, current_qs):
    query_string = urllib.parse.parse_qs(current_qs[1:])
    highlight_entities = set(query_string.get("highlight_entities", []))
    if click_data:
        # Hack: extract practice id from chart label data, which looks
        # like this: {'points': [{'curveNumber': 0, 'x': '2016-05-01',
        # 'y': 'practice 84', 'z': 86.10749488t62395}]}. I think
        # there's a cleaner way to pass ids as chart metadata
        entity_id = click_data["points"][0]["y"].split(" ")[-1]
        highlight_entities.add(entity_id)

    page_state = get_state(page_state)
    if page_state.get("page_id") != settings.CHART_ID:
        return html.Div()

    numerators = page_state.get("numerators", [])
    denominators = page_state.get("denominators", [])
    result_filter = page_state.get("result_filter", [])
    groupby = page_state.get("groupby", None)

    col_name = groupby

    trace_df = get_count_data(
        numerators=numerators,
        denominators=denominators,
        result_filter=result_filter,
        by=col_name,
        hide_entities_with_sparse_data=page_state.get("sparse_data_toggle"),
    )
    deciles_traces = get_practice_decile_traces(trace_df)
    if not deciles_traces:
        return html.Div()
    months = deciles_traces[0].x
    if col_name in ["practice_id", "ccg_id"] and "all" not in highlight_entities:
        entity_ids = get_sorted_group_keys(
            trace_df[trace_df[groupby].isin(highlight_entities)], col_name
        )
    else:
        entity_ids = get_sorted_group_keys(trace_df, col_name)
    traces = deciles_traces[:]
    for entity_id in entity_ids:
        entity_df = trace_df[trace_df[col_name] == entity_id]
        # First, plot the practice line
        traces.append(
            go.Scatter(
                x=entity_df["month"],
                y=entity_df["calc_value"],
                text=entity_df["label"],
                hoverinfo="text",
                name=str(entity_id),
                line=dict(color="red", width=1, dash="solid"),
            )
        )
        if entity_df["calc_value_error"].sum() > 0:
            # If there's any error, bounds and fill
            traces.append(
                go.Scatter(
                    x=entity_df["month"],
                    y=entity_df["calc_value"] + entity_df["calc_value_error"],
                    name=str(entity_id),
                    line=dict(color="red", width=1, dash="dot"),
                    hoverinfo="skip",
                )
            )
            traces.append(
                go.Scatter(
                    x=entity_df["month"],
                    y=entity_df["calc_value"] - entity_df["calc_value_error"],
                    name=str(entity_id),
                    fill="tonexty",
                    line=dict(color="red", width=1, dash="dot"),
                    hoverinfo="skip",
                )
            )
    title = get_chart_title(numerators, denominators, result_filter, list(entity_ids))
    return (
        {
            "data": traces,
            "layout": go.Layout(
                title=title,
                height=450,
                xaxis={"range": [months[0], months[-1]]},
                showlegend=False,
            ),
        },
        "?" + "&".join([f"highlight_entities={x}" for x in highlight_entities]),
    )  # XXX do this properly
