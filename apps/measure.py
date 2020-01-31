import logging
import urllib
from itertools import cycle

import pandas as pd
import plotly.graph_objs as go
from dash.dependencies import Input, Output, State
import dash_core_components as dcc

import numpy as np
from app import app
from apps.base import get_sorted_group_keys
from apps.base import (
    get_title_fragment,
    humanise_list,
    humanise_result_filter,
    humanise_column_name,
    initial_capital,
)
from data import humanise_entity_name
from data import get_count_data
from stateful_routing import get_state
import settings


logger = logging.getLogger(__name__)


DISPLAY_NONE = {"display": "none"}
DISPLAY_SHOW = {"display": ""}

EMPTY_RESPONSE = (settings.EMPTY_CHART_LAYOUT, DISPLAY_NONE, "")


def get_deciles(df):
    """Compute deciles across `calc_value` for each month.

    Returns a list of (decile, value) tuples (e.g. (10, 4.223))
    """
    deciles = np.array(range(10, 100, 10))
    vals_by_month = df.pivot(columns="month", values="calc_value")
    deciles_data = np.nanpercentile(vals_by_month, axis=0, q=deciles)
    return zip(deciles, deciles_data)


def get_decile_traces(df, col_name, highlight_median=False):
    """Return a set of `Scatter` traces  suitable for adding to a Dash figure
    """
    deciles_traces = []
    months = pd.to_datetime(df["month"].unique())
    showlegend = True
    for n, decile in get_deciles(df):
        legend_text = f"Deciles over all<br>available {humanise_column_name(col_name)}<br>nationally"
        legendgroup = "deciles"
        color = settings.DECILE_COLOUR
        style = "dot"
        if n == 50:
            if highlight_median:
                style = "solid"
                color = "red"
                legend_text = legendgroup = "Median"
                showlegend = True
            else:
                style = "dash"

        deciles_traces.append(
            go.Scatter(
                x=months,
                y=decile,
                legendgroup=legendgroup,
                name=legend_text,
                line=dict(color=color, width=1, dash=style),
                hoverinfo="skip",
                showlegend=showlegend,
            )
        )
        # Only show legend for first decile trace
        showlegend = False
    return deciles_traces


@app.callback(
    Output("measure-container", "children"), [Input("page-state", "children")]
)
def update_measures(page_state):
    page_state = get_state(page_state)
    if page_state.get("page_id") != settings.MEASURE_ID:
        return []
    measures = [
        {
            "id": 1,
            "numerators": ["CREA"],
            "denominators": ["CREA", "ESR", "PV"],
            "result_filter": "all",
        },
        {
            "id": 2,
            "numerators": ["K"],
            "denominators": ["per1000"],
            "result_filter": "all",
        },
        {
            "id": 3,
            "numerators": ["TSH"],
            "denominators": ["per1000"],
            "result_filter": "all",
        },
        {
            "id": 4,
            "numerators": ["TSH"],
            "denominators": ["TSH"],
            "result_filter": "under_range",
        },
    ]
    charts = []
    groupby = col_name = page_state.get("groupby", None)
    ccg_ids_for_practice_filter = page_state.get("ccg_ids_for_practice_filter", [])
    lab_ids_for_practice_filter = page_state.get("lab_ids_for_practice_filter", [])
    sparse_data_toggle = page_state.get("sparse_data_toggle", [])
    for measure in measures:
        numerators = measure["numerators"]
        denominators = measure["denominators"]
        result_filter = measure["result_filter"]

        trace_df = get_count_data(
            numerators=measure["numerators"],
            denominators=measure["denominators"],
            result_filter=measure["result_filter"],
            lab_ids_for_practice_filter=lab_ids_for_practice_filter,
            ccg_ids_for_practice_filter=ccg_ids_for_practice_filter,
            by=col_name,
            hide_entities_with_sparse_data=sparse_data_toggle,
        )

        if trace_df.empty:
            return []

        # Don't show deciles in cases where they don't make sense
        if len(trace_df[col_name].unique()) < 10 or groupby == "result_category":
            show_deciles = False
        else:
            show_deciles = True
        highlight_entities = page_state.get("highlight_entities", [])
        if show_deciles or highlight_entities:
            entity_ids = get_sorted_group_keys(
                trace_df[trace_df[col_name].isin(highlight_entities)], col_name
            )
        # If we're not showing deciles, and no entities have been
        # explicitly selected, then we want to display all entities
        # automatically
        else:
            entity_ids = get_sorted_group_keys(trace_df, col_name)

        traces = (
            get_decile_traces(trace_df, col_name, highlight_median=not entity_ids)
            if show_deciles
            else []
        )

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

        fragment = get_title_fragment(numerators, denominators, result_filter)

        if entity_ids:
            fragment = initial_capital(fragment)
            if col_name == "test_code":
                title = get_title_fragment(entity_ids, denominators, result_filter)
            elif col_name == "result_category":
                category_list = humanise_list(
                    [humanise_result_filter(x) for x in entity_ids]
                )
                title = f"{fragment} {category_list}"
            else:
                entity_desc = humanise_column_name(
                    col_name, plural=len(entity_ids) != 1
                )
                title = f"{fragment} at {entity_desc} {humanise_list(entity_ids)}"
            title += f"<br>(with deciles over all {humanise_column_name(col_name)})"
        else:
            title = f"Deciles for {fragment} over all {humanise_column_name(col_name)}"

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
                )
            )

        all_x_vals = set().union(*[trace.x for trace in traces])

        figure = {
            "data": traces,
            "layout": go.Layout(
                title=title,
                height=350,
                xaxis={"range": [min(all_x_vals), max(all_x_vals)]},
                showlegend=True,
                legend={"orientation": "v"},
                annotations=annotations,
            ),
        }
        charts.append(dcc.Graph(id=str(measure["id"]), figure=figure))
    print("XXXXXXXXXXXXXXXXXXXXXXXX {}".format(len(charts)))
    return charts
