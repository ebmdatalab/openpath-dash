import logging
import json

from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go

from app import app
from apps.base import filter_entity_ids_for_type
from apps.base import get_yaxis_label
from apps.base import humanise_column_name
from apps.linecharts import get_chart_components
from stateful_routing import get_state
from urls import urls
import settings

logger = logging.getLogger(__name__)


def analyse_url(measure_state):
    url_args = measure_state.copy()
    url_args["page_id"] = "chart"
    url_args["highlight_entities"] = filter_entity_ids_for_type(
        measure_state.get("groupby", None), measure_state.get("highlight_entities", [])
    )

    return urls.build("analysis", url_args, append_unknown=True)


@app.callback(
    Output("measure-container", "children"), [Input("page-state", "children")]
)
def update_measures(page_state):
    page_state = get_state(page_state)
    if page_state.get("page_id") != settings.MEASURE_ID:
        return []
    with open("apps/measures.json", "rb") as f:
        measures = json.load(f)
    charts = []

    for measure_num, measure in enumerate(measures):
        measure_state = page_state.copy()
        measure_state.update(measure)
        traces, title, annotations = get_chart_components(measure_state)
        yaxis_label = get_yaxis_label(measure_state)
        url = analyse_url(measure_state)
        all_x_vals = set().union(*[trace.x for trace in traces])

        figure = {
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
        charts.append(dcc.Graph(id=str(measure_num), figure=figure))
        charts.append(
            html.Div(
                children=[
                    html.Strong("Why it matters: "),
                    measure["description"] + " ",
                    dcc.Link(
                        f"Customise this measure, including heatmap for all {humanise_column_name(page_state['groupby'])}",
                        href=url,
                    ),
                ],
                className="measure-description",
            )
        )
        charts.append(html.Hr())
    return charts
