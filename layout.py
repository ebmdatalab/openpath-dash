import dash_daq as daq
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
    # Default values for URL arguments which are required but don't form part
    # of the measure definition
    url_args = {"calc_value_range_filter": [0, 100]}
    drop_keys = ["title", "description"]
    url_args.update((x, y) for x, y in measure.items() if x not in drop_keys)
    measure_url = urls.build("analysis", url_args)

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
            dcc.Location(id="url-for-update", refresh=False),
        ]
    )
    numerators_form = dbc.FormGroup(
        [
            dbc.Label("Numerators"),
            dcc.Dropdown(
                id="numerators-dropdown",
                multi=True,
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
            dbc.Label("Filter tests by result type"),
            dcc.Dropdown(
                id="test-filter-dropdown",
                options=[
                    {"value": "all", "label": "All tests with results"},
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
                    if x > 1
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
                    {"value": "practice", "label": "Practice"},
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
    datatable_toggle_form = dbc.FormGroup(
        [
            daq.ToggleSwitch(
                id="datatable-toggle", label="Show raw practice-level data", value=False
            )
        ]
    )
    calc_value_range_filter_form = dbc.FormGroup(
        [
            dbc.Label("Trim extreme values (percent)"),
            dcc.RangeSlider(
                id="calc-value-range-slider",
                min=0,
                max=100,
                step=1,
                value=[0, 100],
                tooltip={"always_visible": True, "placement": "bottom"},
            ),
        ]
    )
    chart_selector_tabs = dbc.Tabs(
        id="chart-selector-tabs",
        active_tab="heatmap",
        children=[
            dbc.Tab(label="Heatmap", tab_id="heatmap"),
            dbc.Tab(label="Counts", tab_id="counts"),
            dbc.Tab(label="Deciles", tab_id="deciles"),
        ],
    )
    form = dbc.Container(
        dbc.Row(
            [
                dbc.Col([numerators_form, denominators_form, groupby_form]),
                dbc.Col(
                    [
                        filters_form,
                        ccg_filter_form,
                        calc_value_range_filter_form,
                        datatable_toggle_form,
                    ]
                ),
            ]
        )
    )
    body = dbc.Container(
        dbc.Row(
            dbc.Col(
                html.Div(
                    [
                        html.Div(id="description-container"),
                        html.Div(id="error-container"),
                        chart_selector_tabs,
                        # All the charts we're interested in, in a spinner container
                        dcc.Loading(
                            id="loading-heatmap",
                            children=[
                                # We make empty graph objects for every graph we might
                                # draw, and show/hide them based on current state
                                html.Div(
                                    id="heatmap-container",
                                    style={"display": "none"},
                                    children=[dcc.Graph(id="heatmap-graph")],
                                ),
                                html.Div(
                                    id="counts-container",
                                    style={"display": "none"},
                                    children=[dcc.Graph(id="counts-graph")],
                                ),
                                html.Div(
                                    id="deciles-container", style={"display": "block"}
                                ),
                                html.Div(
                                    id="measures-container",
                                    style={"display": "none"},
                                    children=make_index_content(measures),
                                ),
                            ],
                        ),
                        html.Div(
                            id="counts-table-container",
                            style={"display": "none"},
                            children=[
                                dcc.Loading(
                                    id="loading-table",
                                    children=[
                                        dash_table.DataTable(
                                            id="counts-table",
                                            columns=[
                                                {
                                                    "name": "month",
                                                    "id": "month",
                                                    "type": "datetime",
                                                },
                                                {"name": "test", "id": "test_code"},
                                                {
                                                    "name": "result",
                                                    "id": "result_category",
                                                },
                                                {"name": "ccg", "id": "ccg_id"},
                                                {
                                                    "name": "practice",
                                                    "id": "practice_id",
                                                },
                                                {
                                                    "name": "numerator",
                                                    "id": "numerator",
                                                },
                                                {
                                                    "name": "denominator",
                                                    "id": "denominator",
                                                },
                                            ],
                                            filter_action="native",
                                            sort_action="native",
                                            sort_mode="multi",
                                            page_action="native",
                                            page_current=0,
                                            page_size=50,
                                        )
                                    ],
                                )
                            ],
                        ),
                    ]
                )
            )
        )
    )
    dash_app = html.Div([state_components, form, body])
    return dash_app
