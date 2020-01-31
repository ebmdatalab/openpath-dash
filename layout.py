import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_table
import settings


OPTION_SEPARATOR = {"value": "__sep__", "label": "\u2015" * 16, "disabled": True}

# This ensures that downloaded graph images match the size shown on screen
COMMON_GRAPH_CONFIG = {"toImageButtonOptions": {"width": None, "height": None}}


def pairs(seq):
    i = iter(seq)
    for item in i:
        try:
            item_2 = next(i)
        except StopIteration:
            item_2 = None
        yield item, item_2


def layout(tests_df, ccgs_list, labs_list, practices_list):
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
        ],
        id="numerators-form",
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
                        "label": "Proportion of numeric results within reference range",
                    },
                    {
                        "value": "under_range",
                        "label": "Proportion of numeric results under reference range",
                    },
                    {
                        "value": "over_range",
                        "label": "Proportion of numeric results over reference range",
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
        ],
        id="denominators-form",
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
                    {"value": "lab_id", "label": "Lab"},
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
    lab_filter_form = dbc.FormGroup(
        [
            dbc.Label("Showing which labs?"),
            dcc.Dropdown(
                id="lab-dropdown",
                multi=True,
                options=[{"value": "all", "label": "All labs"}] + labs_list,
            ),
        ]
    )
    org_focus_form = dbc.FormGroup(
        [
            dbc.Label("Focusing on which organisations?"),
            dcc.Dropdown(
                id="org-focus-dropdown",
                multi=True,
                options=practices_list + labs_list + ccgs_list,
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
    sort_order_form = dbc.FormGroup(
        [dcc.Dropdown(id="sort-order-dropdown", clearable=False)]
    )
    chart_selector_tabs = dbc.Tabs(
        id="chart-selector-tabs",
        active_tab="measure",
        children=[
            dbc.Tab(label="Compare measures", tab_id="measure"),
            dbc.Tab(label="Compare organisations", tab_id="chart"),
            dbc.Tab(label="Data table", tab_id="datatable"),
        ],
    )
    result_category_hint = html.Div(
        [
            "This chart uses reference ranges. Reference ranges need to be treated ",
            "with caution: for example, they may change over time. See our ",
            html.A("FAQ", href="/faq#result-categories"),
            " for more details",
        ],
        id="result-category-hint",
        className="alert alert-info",
        style={"display": "none"},
    )
    form = dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        [
                            numerators_form,
                            denominators_form,
                            groupby_form,
                            org_focus_form,
                        ]
                    ),
                    dbc.Col([ccg_filter_form, lab_filter_form, tweak_form]),
                ]
            ),
            result_category_hint,
        ]
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
                                            children=[
                                                dcc.Graph(
                                                    id="deciles-graph",
                                                    config=COMMON_GRAPH_CONFIG,
                                                )
                                            ],
                                        )
                                    ],
                                )
                            ),
                            html.Div(
                                dcc.Loading(
                                    id="loading-heatmap",
                                    children=[
                                        # We use Markdown component so we can insert
                                        # line breaks as new paragraphs. We add a
                                        # custom CSS rule to remove bottom margin from
                                        # child P elements.
                                        dcc.Markdown(
                                            "",
                                            id="heatmap-click-hint",
                                            className="alert alert-info text-center",
                                            style={"display": "none"},
                                        ),
                                        dbc.Row(
                                            id="sort-order-dropdown-container",
                                            children=[
                                                dbc.Col(
                                                    sort_order_form,
                                                    width={"size": 6, "offset": 6},
                                                )
                                            ],
                                        ),
                                        html.Div(
                                            id="heatmap-container",
                                            children=[
                                                dcc.Graph(
                                                    id="heatmap-graph",
                                                    config=COMMON_GRAPH_CONFIG,
                                                )
                                            ],
                                        ),
                                    ],
                                )
                            ),
                        ],
                    )
                )
            ),
            dbc.Row(
                dbc.Col(
                    dcc.Loading(
                        id="loading-measures",
                        children=[
                            html.Div(
                                id="measure-container",
                                style={"display": "none"},
                                children=[],
                            )
                        ],
                    )
                )
            ),
            dbc.Row(
                dbc.Col(
                    dcc.Loading(
                        id="loading-datatable",
                        children=[
                            html.Div(
                                id="datatable-container",
                                style={"display": "none"},
                                children=[
                                    dash_table.DataTable(
                                        id="datatable",
                                        sort_action="custom",
                                        sort_mode="multi",
                                        page_action="custom",
                                        page_current=0,
                                        page_size=50,
                                    ),
                                    html.Div(
                                        className="download-link-container",
                                        children=[
                                            html.A(
                                                "Download as CSV",
                                                id="datatable-download-link",
                                                href="#",
                                                className="btn btn-outline-primary",
                                            )
                                        ],
                                    ),
                                ],
                            )
                        ],
                    )
                )
            ),
        ]
    )
    dash_app = html.Div([state_components, form, body])
    return dash_app
