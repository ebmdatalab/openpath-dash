import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
from urls import urls
import settings


OPTION_SEPARATOR = {"value": "__sep__", "label": "\u2015" * 16, "disabled": True}


def pairs(seq):
    i = iter(seq)
    for item in i:
        try:
            item_2 = next(i)
        except StopIteration:
            item_2 = None
        yield item, item_2


def layout(tests_df, ccgs_list):
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
            dbc.Label("Select tests"),
            dcc.Dropdown(
                id="numerators-dropdown",
                multi=True,
                value=["CREA"],
                # XXX use clientside javascript to make "all tests"
                # disappear if you select just one:
                # https://community.plot.ly/t/dash-0-41-0-released/22131
                options=[{"value": "all", "label": "All tests"}]
                + tests_df.to_dict("records"),
            ),
        ]
    )

    denominators_form = dbc.FormGroup(
        [
            dbc.Label("Showing"),
            dcc.Dropdown(
                id="denominators-dropdown",
                options=[
                    {"value": "per1000", "label": "Number of tests per 1000 patients"},
                    {"value": "raw", "label": "Number of tests"},
                    OPTION_SEPARATOR,
                    {
                        "value": "within_range",
                        "label": "Proportion of results within reference range",
                    },
                    {
                        "value": "under_range",
                        "label": "Proportion of results under reference range",
                    },
                    {
                        "value": "over_range",
                        "label": "Proportion of results over reference range",
                    },
                    {
                        "value": settings.ERR_NO_REF_RANGE,
                        "label": "Proportion of results where no reference range available",
                    },
                    {
                        "value": settings.ERR_UNPARSEABLE_RESULT,
                        "label": "Proportion of non-numeric results",
                    },
                    OPTION_SEPARATOR,
                    {"value": "other", "label": "Compared with other test numbers"},
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
                    {"value": "result_category", "label": "Result type"},
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
    result_category_hint = html.P(
        [
            "* for more detail on reference ranges and result codes see the ",
            html.A("FAQ", href="/faq#result-categories"),
        ],
        id="result-category-hint",
        className="text-muted",
        style={"display": "none"},
    )
    form = dbc.Container(
        dbc.Row(
            [
                dbc.Col(
                    [
                        numerators_form,
                        denominators_form,
                        groupby_form,
                        result_category_hint,
                    ]
                ),
                dbc.Col([ccg_filter_form, tweak_form]),
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
                dbc.Col(
                    html.Div(
                        id="chart-container",
                        style={"display": "none"},
                        children=[
                            html.Div(
                                dcc.Loading(
                                    id="loading-deciles",
                                    style={"height": "350px"},
                                    children=[
                                        html.Div(
                                            id="deciles-container",
                                            children=[dcc.Graph(id="deciles-graph")],
                                        )
                                    ],
                                )
                            ),
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
                        ],
                    )
                )
            ),
            dbc.Row(
                dbc.Col(
                    [
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
                                    sort_action="custom",
                                    sort_mode="multi",
                                    page_action="custom",
                                    page_current=0,
                                    page_size=50,
                                )
                            ],
                        )
                    ]
                )
            ),
        ]
    )
    dash_app = html.Div([state_components, form, body])
    return dash_app
