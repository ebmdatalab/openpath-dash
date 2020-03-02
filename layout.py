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
                value=[],
                # XXX use clientside javascript to make "all tests"
                # disappear if you select just one:
                # https://community.plot.ly/t/dash-0-41-0-released/22131
                options=tests_df.to_dict("records"),
                placeholder="Start typing",
            ),
        ],
        id="numerators-form",
        style={"display": "none"},
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
                placeholder="Start typing",
                options=tests_df.to_dict("records"),
                style={"display": "none"},
            ),
        ],
        id="denominators-form",
        style={"display": "none"},
    )
    groupby_form = dbc.FormGroup(
        [
            dbc.Label("Group by", id="groupby-label"),
            dcc.Dropdown(
                id="groupby-dropdown", options=settings.ANALYSE_DROPDOWN_OPTIONS
            ),
        ]
    )
    ccg_filter_form = dbc.FormGroup(
        [
            dbc.Label("Filter to specific CCGs"),
            dcc.Dropdown(id="ccg-dropdown", multi=True, options=ccgs_list),
        ]
    )
    lab_filter_form = dbc.FormGroup(
        [
            dbc.Label("Filter to specific labs", id="lab-focus-label"),
            dcc.Dropdown(id="lab-dropdown", multi=True, options=labs_list),
        ]
    )
    org_focus_form = dbc.FormGroup(
        [
            dbc.Label("Higlight specific organisation", id="org-focus-label"),
            dcc.Dropdown(
                id="org-focus-dropdown",
                multi=True,
                options=practices_list + labs_list + ccgs_list,
                placeholder="Start typing",
            ),
        ],
        id="org-focus-form",
        style={"display": "none"},
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
    measures_tab_text = dbc.Row(
        dbc.Col(
            html.Div(
                "This page lists several measures that we think may be of interest for comparing labs, CCGs or practices.  Under each chart is an explanation of why it matters, and a link to drill down deeper into that measure.  Use the 'compare by' field below to switch between comparing practices, labs, or CCGs. When there are too many comparisons to make at once, we show deciles; use the 'highlight' field in the form to add lines to the chart individually. ",
                className="alert alert-info",
            )
        )
    )
    custom_tab_text = dbc.Row(
        dbc.Col(
            html.Div(
                "This page allows you to create or explore a single measure. When there are too many comparisons to make at once, we just show deciles; click a row in the heatmap to add lines to the chart individually. ",
                className="alert alert-info",
            )
        )
    )
    data_tab_text = dbc.Row(
        dbc.Col(
            html.Div(
                "This page shows all data at a practice level for the currently-selected filters",
                className="alert alert-info",
            )
        )
    )
    chart_selector_tabs = dbc.Tabs(
        id="chart-selector-tabs",
        active_tab="measure",
        children=[
            dbc.Tab(
                label="All predefined measures",
                tab_id="measure",
                children=[measures_tab_text],
            ),
            dbc.Tab(
                label="Custom measure (+ heatmap)",
                tab_id="chart",
                id="org-tab-label",
                children=[custom_tab_text],
            ),
            dbc.Tab(
                label="Download data", tab_id="datatable", children=[data_tab_text]
            ),
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
    header = dbc.Row(
        dbc.Col(
            html.Div(
                [
                    html.Div(id="description-container"),
                    html.Div(id="error-container"),
                    chart_selector_tabs,
                ]
            )
        )
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
                                    html.Hr(),
                                    dash_table.DataTable(
                                        id="datatable",
                                        sort_action="custom",
                                        sort_mode="multi",
                                        page_action="custom",
                                        page_current=0,
                                        page_size=50,
                                    ),
                                ],
                            )
                        ],
                    )
                )
            ),
        ]
    )
    dash_app = html.Div([state_components, header, form, body])
    return dash_app
