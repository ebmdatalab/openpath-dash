import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
from urls import urls
import settings


def pairs(seq):
    i = iter(seq)
    for item in i:
        try:
            item_2 = next(i)
        except StopIteration:
            item_2 = None
        yield item, item_2


def make_measure_card(measure):
    drop_keys = ["title", "description"]
    measure_url = urls.build(
        "analysis", dict((x, y) for x, y in measure.items() if x not in drop_keys)
    )

    return dbc.Card(
        [
            dbc.CardBody(
                [
                    html.H4(measure["title"], className="card-title"),
                    html.P(measure["description"]),
                    dcc.Link("Read more", href=measure_url),
                ]
            )
        ],
        className="mb3",
    )


def make_index_content(measures):
    container = dbc.Container()
    rows = []
    for x, y in pairs(measures.to_dict("records")):
        row = dbc.Row()
        cols = []
        if x:
            cols.append(dbc.Col(make_measure_card(x)))
        if y:
            cols.append(dbc.Col(make_measure_card(y)))
        row.children = cols
        rows.append(row)
    container.children = rows
    return container


def layout(tests_df, ccgs_list, measures):
    state_components = html.Div(
        [
            # Hidden div inside the app that stores the page state
            # XXX possibly use https://dash.plot.ly/dash-core-components/store
            html.Pre(id="page-state", style={"display": "none"}),
            # Two "locations" with the same function, to allow two
            # different callbacks to use them without cycles in the
            # graph.  This one represents URLs from the user,
            # i.e. bookmarked or directly edited
            dcc.Location(id="url-from-user", refresh=False),
            # This one represents the URL that was want to change to
            # reflect the current page state
            dcc.Location(id="url-for-update", refresh=True),
        ]
    )
    numerators_form = dbc.FormGroup(
        [
            dbc.Label("Numerators"),
            dcc.Dropdown(
                id="numerators-dropdown",
                multi=True,
                value=["K"],
                # XXX use clientside javascript to make "all tests"
                # disappear if you select just one:
                # https://community.plot.ly/t/dash-0-41-0-released/22131
                options=[{"value": "all", "label": "All tests"}]
                + tests_df.to_dict("records"),
            ),
        ]
    )

    filters_form = dbc.FormGroup(
        [
            dbc.Label("Filter numerator"),
            dcc.Dropdown(
                id="test-filter-dropdown",
                options=[
                    {"value": "all", "label": "No filter"},
                    {
                        "value": "within_range",
                        "label": "Results within reference range",
                    },
                    {"value": "under_range", "label": "Results under reference range"},
                    {"value": "over_range", "label": "Results over reference range"},
                ]
                + [
                    {"value": x, "label": "Specific error: " + y}
                    for x, y in settings.ERROR_CODES.items()
                    if x > 1 and x < 4
                ],
            ),
        ]
    )
    denominators_form = dbc.FormGroup(
        [
            dbc.Label("Denominators"),
            dcc.Dropdown(
                id="denominators-dropdown",
                options=[
                    {"value": "per1000", "label": "Per 1000 patients"},
                    {"value": "raw", "label": "Raw numbers"},
                    {"value": "other", "label": "As a proportion of other tests"},
                ],
            ),
            dcc.Dropdown(
                id="denominator-tests-dropdown",
                multi=True,
                placeholder="Select tests",
                options=tests_df.to_dict("records"),
                style={"display": "none"},
            ),
        ]
    )
    groupby_form = dbc.FormGroup(
        [
            dbc.Label("Group by"),
            dcc.Dropdown(
                id="groupby-dropdown",
                options=[
                    {"value": "practice_id", "label": "Practice"},
                    {"value": "test_code", "label": "Test code"},
                    {"value": "ccg_id", "label": "CCG"},
                    {"value": "result_category", "label": "Result"},
                ],
            ),
        ]
    )
    ccg_filter_form = dbc.FormGroup(
        [
            dbc.Label("Showing which CCGs?"),
            dcc.Dropdown(
                id="ccg-dropdown",
                multi=True,
                options=[{"value": "all", "label": "All CCGs"}] + ccgs_list,
            ),
        ]
    )
    tweak_form = dbc.FormGroup(
        [
            dbc.Checklist(
                id="tweak-form",
                options=[
                    {
                        "label": "Hide organisations with low numbers",
                        "value": "suppress_sparse_data",
                    },
                    {"label": "Equalise heatmap colours", "value": "equalise_colours"},
                ],
                value=["suppress_sparse_data"],
            )
        ]
    )
    chart_selector_tabs = dbc.Tabs(
        id="chart-selector-tabs",
        active_tab="chart",
        children=[
            dbc.Tab(label="Chart", tab_id="chart"),
            dbc.Tab(label="Practice-level data table", tab_id="datatable"),
        ],
    )
    form = dbc.Container(
        dbc.Row(
            [
                dbc.Col([numerators_form, denominators_form, groupby_form]),
                dbc.Col([filters_form, ccg_filter_form, tweak_form]),
            ]
        )
    )
    body = dbc.Container(
        [
            dbc.Row(
                dbc.Col(
                    html.Div(
                        [
                            html.Div(id="description-container"),
                            html.Div(id="error-container"),
                            chart_selector_tabs,
                        ]
                    )
                )
            ),
            dbc.Row(
                [
                    dbc.Col(
                        html.Div(
                            # All the charts we're interested in, in a spinner container
                            dcc.Loading(
                                id="loading-deciles",
                                style={"height": "350px"},
                                children=[
                                    html.Div(
                                        id="deciles-container",
                                        children=[dcc.Graph(id="deciles-graph")],
                                        className="position-fixed",
                                    )
                                ],
                            )
                        ),
                        width=7,
                    ),
                    dbc.Col(
                        html.Div(
                            dcc.Loading(
                                id="loading-heatmap",
                                children=[
                                    html.Div(
                                        id="heatmap-container",
                                        children=[dcc.Graph(id="heatmap-graph")],
                                    )
                                ],
                            )
                        ),
                        width=5,
                    ),
                ],
                id="chart-container",
                style={"display": "none"},
            ),
            dbc.Row(
                dbc.Col(
                    [
                        html.Div(
                            id="measures-container",
                            style={"display": "none"},
                            children=make_index_content(measures),
                        ),
                        html.Div(
                            id="datatable-container",
                            style={"display": "none"},
                            children=[
                                dash_table.DataTable(
                                    id="datatable",
                                    columns=[
                                        {
                                            "name": "month",
                                            "id": "month",
                                            "type": "datetime",
                                        },
                                        {"name": "test", "id": "test_code"},
                                        {"name": "result", "id": "result_category"},
                                        {"name": "ccg", "id": "ccg_id"},
                                        {"name": "practice", "id": "practice_id"},
                                        {"name": "numerator", "id": "numerator"},
                                        {"name": "denominator", "id": "denominator"},
                                    ],
                                    filter_action="native",
                                    sort_action="native",
                                    sort_mode="multi",
                                    page_action="native",
                                    page_current=0,
                                    page_size=50,
                                )
                            ],
                        ),
                    ]
                )
            ),
        ]
    )
    dash_app = html.Div([state_components, form, body])
    return dash_app
