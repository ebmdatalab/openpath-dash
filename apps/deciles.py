import logging
import urllib
from itertools import cycle

import dash_html_components as html
import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State

import numpy as np
from app import app
from apps.base import get_sorted_group_keys
from apps.base import get_chart_title
from apps.base import humanise_entity_name
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
    added_legend = False
    for n, decile in get_practice_deciles(df):
        if n == 50:
            style = "dash"
        else:
            style = "dot"
        if not added_legend:
            showlegend = True
            added_legend = True
        else:
            showlegend = False
        deciles_traces.append(
            go.Scatter(
                x=months,
                y=decile,
                legendgroup="deciles",
                name="deciles",
                line=dict(color=settings.DECILE_COLOUR, width=1, dash=style),
                hoverinfo="skip",
                showlegend=showlegend,
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
    page_state = get_state(page_state)

    EMPTY_RESPONSE = (settings.EMPTY_CHART_LAYOUT, "")

    if page_state.get("page_id") != settings.CHART_ID:
        return EMPTY_RESPONSE

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
    if trace_df.empty:
        return EMPTY_RESPONSE
    deciles_traces = get_practice_decile_traces(trace_df)

    # Remove any highlight entities that are not a valie groupby key
    # (for example, practice ids when we're grouping by ccg id)
    available_entities = trace_df[groupby].unique()
    highlight_entities = list(
        np.intersect1d(query_string.get("highlight_entities", []), available_entities)
    )

    if click_data:
        entity_label = click_data["points"][0]["y"]
        # Hack: get the entity_id from the Y-axis label by working out the
        # labels for all entities and finding the one which matches. It ought
        # to be possible to pass the entity_id through using the `customdata`
        # property but this seems to have been broken for the last couple of
        # years. See:
        # https://community.plot.ly/t/plotly-dash-heatmap-customdata/5871
        for entity_id in available_entities:
            if entity_label == humanise_entity_name(col_name, entity_id):
                break
        else:
            entity_id = None
        if entity_id not in highlight_entities:
            highlight_entities.append(entity_id)
        else:
            highlight_entities.remove(entity_id)

    entity_ids = get_sorted_group_keys(
        trace_df[trace_df[groupby].isin(highlight_entities)], col_name
    )
    traces = deciles_traces[:]
    months = deciles_traces[0].x
    entity_names = []
    for colour, entity_id in zip(cycle(settings.LINE_COLOUR_CYCLE), entity_ids):
        entity_name = humanise_entity_name(col_name, entity_id)
        entity_names.append(entity_name)
        entity_df = trace_df[trace_df[col_name] == entity_id]
        # First, plot the practice line
        traces.append(
            go.Scatter(
                legendgroup=entity_id,
                x=entity_df["month"],
                y=entity_df["calc_value"],
                text=entity_df["label"],
                hoverinfo="text",
                name=entity_name,
                line_width=2,
                line=dict(color=colour, width=1, dash="solid"),
            )
        )
        if entity_df["calc_value_error"].sum() > 0:
            # If there's any error, bounds and fill
            traces.append(
                go.Scatter(
                    legendgroup=entity_id,
                    x=entity_df["month"],
                    y=entity_df["calc_value"] + entity_df["calc_value_error"],
                    name=str(entity_id),
                    line=dict(color=colour, width=1, dash="dot"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            traces.append(
                go.Scatter(
                    legendgroup=entity_id,
                    x=entity_df["month"],
                    y=entity_df["calc_value"] - entity_df["calc_value_error"],
                    name=str(entity_id),
                    fill="tonexty",
                    line=dict(color=colour, width=1, dash="dot"),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
    title = get_chart_title(numerators, denominators, result_filter, entity_names)
    if not highlight_entities:
        title += "<br><sub>Select a row from the heatmap below to add lines to this chart</sub>"
    return (
        {
            "data": traces,
            "layout": go.Layout(
                title=title,
                height=350,
                xaxis={"range": [months[0], months[-1]]},
                showlegend=True,
                legend={"orientation": "v"},
            ),
        },
        "?" + "&".join([f"highlight_entities={x}" for x in highlight_entities]),
    )  # XXX do this properly
