"""Core declines/line chart drawing, used by both measures and analyse
form

"""
from itertools import cycle
import pandas as pd
import plotly.graph_objs as go

import numpy as np
from apps.base import get_title, filter_entity_ids_for_type
from apps.base import humanise_column_name
from apps.base import linebreakify
from data import humanise_entity_name
from data import get_count_data

import settings


def get_deciles(df):
    """Compute deciles across `calc_value` for each month.

    Returns a list of (decile, value) tuples (e.g. (10, 4.223))
    """
    deciles = np.array(range(10, 100, 10))
    vals_by_month = df.pivot(columns="month", values="calc_value")
    deciles_data = np.nanpercentile(vals_by_month, axis=0, q=deciles)
    return zip(deciles, deciles_data)


def get_decile_traces(
    df,
    col_name,
    ccg_ids_for_practice_filter,
    lab_ids_for_practice_filter,
    highlight_median=False,
):
    """Return a set of `Scatter` traces  suitable for adding to a Dash figure
    """

    deciles_traces = []
    months = pd.to_datetime(df["month"].unique())
    showlegend = True
    for n, decile in get_deciles(df):
        legend_text = f"Deciles over {humanise_column_name(col_name, plural=True)}"
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
                mode="lines",
                hoverinfo="skip",
                showlegend=showlegend,
            )
        )
        # Only show legend for first decile trace
        showlegend = False
    return deciles_traces


def get_chart_components(page_state):
    """Given current page state, return all the bits you need to assemble
    a plotly figure:

    Returns an array of traces; a chart title; hint text giving user
    pointers on what to do next; and an array annotations used for
    explaining the legend.

    """
    numerators = page_state.get("numerators", [])
    denominators = page_state.get("denominators", [])
    result_filter = page_state.get("result_filter", [])
    groupby = page_state.get("groupby", None)
    ccg_ids_for_practice_filter = page_state.get("ccg_ids_for_practice_filter", [])
    lab_ids_for_practice_filter = page_state.get("lab_ids_for_practice_filter", [])

    trace_df = get_count_data(
        numerators=numerators,
        denominators=denominators,
        result_filter=result_filter,
        lab_ids_for_practice_filter=lab_ids_for_practice_filter,
        ccg_ids_for_practice_filter=ccg_ids_for_practice_filter,
        by=groupby,
        hide_entities_with_sparse_data=page_state.get("sparse_data_toggle"),
    )
    if trace_df.empty:
        return [], "", ""

    # Don't show deciles in cases where they don't make sense
    if len(trace_df[groupby].unique()) < 10 or groupby == "result_category":
        show_deciles = False
    else:
        show_deciles = True

    # If we're showing deciles then get the IDs of the highlighted entities so
    # we can display them
    highlight_entities = filter_entity_ids_for_type(
        groupby, page_state.get("highlight_entities", [])
    )
    if show_deciles or highlight_entities:
        entity_ids = sorted(
            trace_df[trace_df[groupby].isin(highlight_entities)][groupby].unique()
        )
        if highlight_entities:
            # Sort by the order they appear in the query string (which
            # should be the order the user added them in)
            entity_ids = [x for x in highlight_entities if x in entity_ids]

    # If we're not showing deciles, and no entities have been
    # explicitly selected, then we want to display all entities
    # automatically
    else:
        entity_ids = sorted(trace_df[groupby].unique())
    highlight_median = not entity_ids
    traces = (
        get_decile_traces(
            trace_df,
            groupby,
            ccg_ids_for_practice_filter,
            lab_ids_for_practice_filter,
            highlight_median=highlight_median,
        )
        if show_deciles
        else []
    )

    has_error_bars = False
    for colour, entity_id in zip(cycle(settings.LINE_COLOUR_CYCLE), entity_ids):
        entity_df = trace_df[trace_df[groupby] == entity_id]
        # First, plot the practice line
        traces.append(
            go.Scatter(
                legendgroup=str(entity_id),
                x=entity_df["month"],
                y=entity_df["calc_value"],
                text=entity_df["label"],
                hoverinfo="text",
                name=humanise_entity_name(groupby, entity_id),
                line_width=2,
                mode="lines",
                line=dict(color=colour, width=1, dash="solid"),
            )
        )
        if entity_df["calc_value_error"].sum() > 0:
            has_error_bars = True
            # If there's any error, bounds and fill
            traces.append(
                go.Scatter(
                    legendgroup=str(entity_id),
                    x=entity_df["month"],
                    y=entity_df["calc_value"] + entity_df["calc_value_error"],
                    name=str(entity_id),
                    line=dict(color=colour, width=1, dash="dot"),
                    mode="lines",
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            traces.append(
                go.Scatter(
                    legendgroup=str(entity_id),
                    x=entity_df["month"],
                    y=entity_df["calc_value"] - entity_df["calc_value_error"],
                    name=str(entity_id),
                    fill="tonexty",
                    line=dict(color=colour, width=1, dash="dot"),
                    mode="lines",
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    title = get_title(
        numerators,
        denominators,
        result_filter,
        show_deciles,
        groupby,
        entity_ids,
        ccg_ids_for_practice_filter,
        lab_ids_for_practice_filter,
    )
    title = linebreakify(title, 100)
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
    return traces, title, annotations
