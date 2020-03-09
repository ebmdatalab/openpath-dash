import logging


from dash.dependencies import Input, Output, State
import plotly.graph_objs as go

from app import app
from apps.base import get_yaxis_label
from apps.linecharts import get_chart_components
from stateful_routing import get_state
import settings


logger = logging.getLogger(__name__)


DISPLAY_NONE = {"display": "none"}

EMPTY_RESPONSE = (settings.EMPTY_CHART_LAYOUT, DISPLAY_NONE, "")


@app.callback(
    Output("deciles-graph", "figure"),
    [Input("page-state", "children")],
    [State("url-for-update", "search")],
)
def update_deciles(page_state, current_qs):
    page_state = get_state(page_state)

    if page_state.get("page_id") != settings.CHART_ID:
        return EMPTY_RESPONSE
    components = get_chart_components(page_state)
    if components:
        traces, title, annotations = components
        if traces:
            yaxis_label = get_yaxis_label(page_state)
            all_x_vals = set().union(*[trace.x for trace in traces])
            chart = {
                "data": traces,
                "layout": go.Layout(
                    title=title,
                    height=350,
                    xaxis={"range": [min(all_x_vals), max(all_x_vals)]},
                    yaxis={"title": {"text": yaxis_label}},
                    showlegend=True,
                    legend={"orientation": "v"},
                    annotations=annotations,
                ),
            }
            return chart
    return EMPTY_RESPONSE
