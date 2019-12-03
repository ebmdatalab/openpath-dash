import logging
import urllib
from itertools import cycle
import dash

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
from apps.base import toggle_entity_id_list_from_click_data
from data import humanise_entity_name
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
    Output("deciles-graph", "figure"),
    [Input("page-state", "children"), Input("heatmap-graph", "clickData")],
    [State("url-for-update", "search")],
)
def update_deciles(page_state, click_data, current_qs):
    ctx = dash.callback_context
    triggered_inputs = [x["prop_id"].split(".")[0] for x in ctx.triggered]
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

    highlight_entities = query_string.get("highlight_entities", [])
    if "heatmap-graph" in triggered_inputs:
        # User has clicked on a cell in the heatmap
        highlight_entities = toggle_entity_id_list_from_click_data(
            click_data, highlight_entities
        )

    entity_ids = get_sorted_group_keys(
        trace_df[trace_df[groupby].isin(highlight_entities)], col_name
    )
    traces = deciles_traces[:]
    months = deciles_traces[0].x
    has_error_bars = False
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
            has_error_bars = True
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
    elif col_name == "lab_id":
        group_name = "labs"
    elif col_name == "test_code":
        group_name = "tests"
    elif col_name == "result_category":
        group_name = "result types"
    else:
        raise ValueError(col_name)

    fragment = get_title_fragment(numerators, denominators, result_filter)

    if entity_ids:
        fragment = initial_capital(fragment)
        s = "s" if len(entity_ids) > 1 else ""
        if col_name == "test_code":
            title = get_title_fragment(entity_ids, denominators, result_filter)
        elif col_name == "practice_id":
            practice_list = humanise_list(entity_ids)
            title = f"{fragment} at practice{s} {practice_list}"
        elif col_name == "ccg_id":
            ccg_list = humanise_list(entity_ids)
            title = f"{fragment} at CCG{s} {ccg_list}"
        elif col_name == "lab_id":
            ccg_list = humanise_list(entity_ids)
            title = f"{fragment} at lab{s} {ccg_list}"
        elif col_name == "result_category":
            category_list = humanise_list(
                [humanise_result_filter(x) for x in entity_ids]
            )
            title = f"{fragment} {category_list}"
        else:
            raise ValueError(col_name)
        title += f"<br>(with deciles over all {group_name})"
    else:
        title = f"Deciles for {fragment} over all {group_name}"
        title += "<br><sub>Select a row from the heatmap below to add lines to this chart</sub>"

    annotations = []
    if has_error_bars:
        annotations.append(
            go.layout.Annotation(
                text=(
                    "* coloured bands indicate uncertainty due to suppression of "
                    'low numbers (<a href="/faq#low-numbers">see FAQ</a>)'
                ),
                font={"color": "#6c757d"},
                xref="paper",
                xanchor="right",
                x=1,
                xshift=120,
                yref="paper",
                yanchor="top",
                y=0,
                yshift=-26,
                showarrow=False,
            ),
        )

    return {
        "data": traces,
        "layout": go.Layout(
            title=title,
            height=350,
            xaxis={"range": [months[0], months[-1]]},
            showlegend=True,
            legend={"orientation": "v"},
            annotations=annotations,
        ),
    }
