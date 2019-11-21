import logging
import urllib
from itertools import cycle

import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State

import numpy as np
from app import app
from apps.base import get_sorted_group_keys
from apps.base import (
    get_title_fragment,
    humanise_list,
    humanise_result_filter,
    initial_capital,
)
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
                name="Deciles",
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
    entities_in_query = query_string.get("highlight_entities", [])
    # Hack: result_category values are ints not strings, but everything gets
    # converted to strings when passed through the URL query params
    if col_name == "result_category":
        entities_in_query = list(map(int, entities_in_query))
    highlight_entities = list(np.intersect1d(entities_in_query, available_entities))

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
    for colour, entity_id in zip(cycle(settings.LINE_COLOUR_CYCLE), entity_ids):
        entity_df = trace_df[trace_df[col_name] == entity_id]
        # First, plot the practice line
        traces.append(
            go.Scatter(
                legendgroup=entity_id,
                x=entity_df["month"],
                y=entity_df["calc_value"],
                text=entity_df["label"],
                hoverinfo="text",
                name=humanise_entity_name(col_name, entity_id),
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

    if col_name == "practice_id":
        group_name = "practices"
    elif col_name == "ccg_id":
        group_name = "CCGs"
    elif col_name == "test_code":
        group_name = "tests"
    elif col_name == "result_category":
        group_name = "result types"
    else:
        raise ValueError(col_name)

    fragment = get_title_fragment(numerators, denominators, result_filter)

    if highlight_entities:
        fragment = initial_capital(fragment)
        s = "s" if len(highlight_entities) > 1 else ""
        if col_name == "test_code":
            title = get_title_fragment(highlight_entities, denominators, result_filter)
        elif col_name == "practice_id":
            practice_list = humanise_list(highlight_entities)
            title = f"{fragment} at practice{s} {practice_list}"
        elif col_name == "ccg_id":
            ccg_list = humanise_list(highlight_entities)
            title = f"{fragment} at CCG{s} {ccg_list}"
        elif col_name == "result_category":
            category_list = humanise_list(
                [humanise_result_filter(x) for x in highlight_entities]
            )
            title = f"{fragment} {category_list}"
        else:
            raise ValueError(col_name)
        title += f"<br>(with deciles over all {group_name})"
    else:
        title = f"Deciles for {fragment} over all {group_name}"
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
