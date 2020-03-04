"""This module is responsible for maintaining state for the user, and
ensuring this state is also reflected in the URL.

The state is stored as stringified JSON stored in a hidden div.

"""
import json
import logging
import dash
import urllib
from urllib.parse import urlencode, quote_plus
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html

from app import app
from data import get_org_list
from apps.base import toggle_entity_id_list_from_click_data
from apps.base import humanise_column_name

from urls import urls
import settings

from werkzeug.routing import NotFound
from werkzeug.routing import BuildError


logger = logging.getLogger(__name__)


def get_state(possible_state_text):
    """Get state from stringifyed JSON, or an empty dict
    """
    try:
        state = json.loads(possible_state_text)
    except (json.decoder.JSONDecodeError, TypeError):
        state = {"update_counter": 0}
    return state


def update_state(state, **kw):
    """Update `state` with keyword values, if they are different from
    current values, and non-null. Keyword values of None or empty
    lists denote that the key should be removed from the state.

    Sets a `_dirty` key if any changes have been made

    """
    if "_dirty" in state:
        del state["_dirty"]
    orig_state = state.copy()
    for k, v in kw.items():
        if isinstance(v, list):
            if not v and k not in state:
                different = False
            else:
                different = len(set(v).symmetric_difference(set(state.get(k, [])))) > 0
        else:
            different = v is not None and state.get(k, "_nevermatches_") != v
        if different:
            if not v:
                if k in state:
                    del state[k]
            else:
                state[k] = v
    if orig_state != state:
        state["_dirty"] = True


@app.callback(Output("url-for-update", "pathname"), [Input("page-state", "children")])
def update_url_from_page_state(page_state):
    """Cause the page location to match the current page state
    """
    page_state = get_state(page_state)
    try:
        url = urls.build("analysis", page_state, append_unknown=False)
        logger.debug("URL %s found from page state %s", url, page_state)
    except BuildError:
        logger.debug("No url found for state %s; PreventUpdate", page_state)
        raise PreventUpdate
    return url


@app.callback(
    [
        Output("numerators-form", "style"),
        Output("denominators-form", "style"),
        Output("groupby-label", "children"),
        Output("groupby-dropdown", "options"),
    ],
    [Input("chart-selector-tabs", "active_tab")],
)
def toggle_numerator_denominator_visibility(active_tab):
    if active_tab == "measure":
        display = "none"
        groupby_label = "Compare by"
        dropdown_options = settings.CORE_DROPDOWN_OPTIONS
    else:
        display = "block"
        groupby_label = "Group by"
        dropdown_options = settings.ANALYSE_DROPDOWN_OPTIONS
    return [{"display": display}, {"display": display}, groupby_label, dropdown_options]


@app.callback(
    Output("org-focus-label", "children"), [Input("groupby-dropdown", "value")]
)
def update_org_labels(groupby):
    name = humanise_column_name(groupby)
    return (f"Highlight specific {name}",)


@app.callback(Output("org-focus-form", "style"), [Input("groupby-dropdown", "value")])
def show_or_hide_org_focus_dropdown(groupby_selector):
    if groupby_selector in ["practice_id", "ccg_id", "lab_id"]:
        return {"display": "block"}
    else:
        return {"display": "none"}


@app.callback(
    Output("page-state", "children"),
    [
        Input("numerators-dropdown", "value"),
        Input("denominators-dropdown", "value"),
        Input("denominator-tests-dropdown", "value"),
        Input("groupby-dropdown", "value"),
        Input("ccg-dropdown", "value"),
        Input("lab-dropdown", "value"),
        Input("chart-selector-tabs", "active_tab"),
        Input("tweak-form", "value"),
        Input("org-focus-dropdown", "value"),
    ],
    [
        State("page-state", "children"),
        State("url-for-update", "pathname"),
        State("url-for-update", "hash"),
    ],
)
def update_state_from_inputs(
    selected_numerator,
    selected_denominator,
    denominator_tests,
    groupby,
    selected_ccg,
    selected_lab,
    selected_chart,
    tweak_form,
    org_focus,
    page_state,
    current_path,
    current_hash,
):
    """
    Given a series of possible user inputs, update the state if it needs to be changed.
    """
    ctx = dash.callback_context
    triggered_inputs = [x["prop_id"].split(".")[0] for x in ctx.triggered]
    page_state = get_state(page_state)
    orig_page_state = page_state.copy()
    selected_chart = selected_chart or "measure"
    selected_numerator = selected_numerator or ["all"]
    selected_denominator = selected_denominator or ["all"]
    selected_ccg = selected_ccg or ["all"]
    selected_lab = selected_lab or ["all"]
    # Infer `selected_filter` value from the denominators dropdown
    if selected_denominator not in ["per1000", "raw", "other"]:
        # It's actually a filter
        selected_filter = selected_denominator
        selected_denominator = "other"
        denominator_tests = selected_numerator
    else:
        selected_filter = "all"
    # Errors should already have been shown by this point. Reset error state.
    if "error" in page_state:
        del page_state["error"]
    try:
        _, url_state = urls.match(current_path)
        update_state(page_state, **url_state)
    except NotFound:
        update_state(
            page_state,
            error={
                "status_code": 404,
                "message": f"Unable to find page at {current_path}",
            },
        )
    if selected_denominator == "other":
        # We store one of raw, per100 or TEST1+TEST in the URL. We
        # always store that as the `denominators` value in the page
        # state, even though the dropdown for selected_numerator may
        # be `other`. This needs cleaning up! XXX
        stored_denominators = denominator_tests
    else:
        stored_denominators = [selected_denominator]
    sparse_data_toggle = "suppress_sparse_data" in tweak_form
    equalise_colorscale = "equalise_colours" in tweak_form
    update_state(
        page_state,
        numerators=selected_numerator,
        denominators=stored_denominators,
        result_filter=selected_filter,
        groupby=groupby,
        ccg_ids_for_practice_filter=selected_ccg,
        lab_ids_for_practice_filter=selected_lab,
        page_id=selected_chart,
        sparse_data_toggle=sparse_data_toggle,
        equalise_colorscale=equalise_colorscale,
        highlight_entities=org_focus,
    )

    # Only trigger state changes if something has changed
    if "_dirty" not in page_state:
        logger.info("State unchanged")
        if current_hash:
            # Propagate event chain, so we don't ignore events
            # involving hash changes
            return json.dumps(page_state)
        else:
            raise PreventUpdate

    del page_state["_dirty"]
    update_state(page_state, update_counter=page_state["update_counter"] + 1)

    logger.info(
        "-- updating state from %s, was %s, now %s",
        triggered_inputs,
        orig_page_state,
        page_state,
    )
    return json.dumps(page_state)


def _get_dropdown_current_value_by_id(component_id):
    """Given a layout, find the component with the specified id, and then
    return the selected value, or if not set, the first value in its
    options

    """
    # XXX find out if this can be made safe to use. Seems like a useful method
    # to make public.
    component = None
    for _, component in app.layout._traverse_with_paths():
        if getattr(component, "id", None) == component_id:
            break
    if component is not None:
        if hasattr(component, "value"):
            return component.value and component.value[0] or ""
        else:
            return component.options[0]["value"]
    else:
        return ""


def _create_dropdown_update_func(selector_id, page_state_key, default, is_multi):
    """Create a callback function that updates a dropdown based on the current URL
    """

    def update_dropdown_from_url(pathname):
        """Cause the specified multi dropdown to match the current page location
        """
        logger.info("-- multi dropdown %s being set from URL %s", selector_id, pathname)
        if pathname:
            # Sometimes None for reasons explained here:
            # https://github.com/plotly/dash/issues/133#issuecomment-330714608
            current_value = _get_dropdown_current_value_by_id(selector_id)
            try:
                _, url_state = urls.match(pathname)
                if page_state_key in url_state:
                    return url_state[page_state_key]
                else:
                    logger.info("****-> %s", current_value)
                    return is_multi and [current_value] or current_value
            except NotFound:
                return default
        raise PreventUpdate

    return update_dropdown_from_url


for selector_id, page_state_key, default, is_multi in [
    ("numerators-dropdown", "numerators", None, True),
    ("denominator-tests-dropdown", "denominators", "", True),
    ("groupby-dropdown", "groupby", "lab_id", False),
    ("ccg-dropdown", "ccg_ids_for_practice_filter", "all", True),
    ("lab-dropdown", "lab_ids_for_practice_filter", "all", True),
]:
    app.callback(Output(selector_id, "value"), [Input("url-from-user", "pathname")])(
        _create_dropdown_update_func(selector_id, page_state_key, default, is_multi)
    )


@app.callback(
    Output("chart-selector-tabs", "active_tab"), [Input("url-from-user", "pathname")]
)
def update_chart_selector_tabs_from_url(pathname):
    if pathname:
        # Sometimes None for reasons explained here:
        # https://github.com/plotly/dash/issues/133#issuecomment-330714608
        try:
            _, url_state = urls.match(pathname)
            return url_state.get("page_id", "measure")
        except NotFound:
            return "measure"
    raise PreventUpdate


# XXX can I use the _create_multi_dropdown_update_func pattern above for this?
@app.callback(
    Output("denominators-dropdown", "value"), [Input("url-from-user", "pathname")]
)
def update_denominator_dropdown_from_url(pathname):
    """Cause the denom dropdown to match the current page location
    """
    logger.info("-- denom dropdown being set from URL %s", pathname)
    if pathname:
        # Sometimes None for reasons explained here:
        # https://github.com/plotly/dash/issues/133#issuecomment-330714608
        try:
            _, url_state = urls.match(pathname)
            # if it's raw, per1000 or other, leave as-is
            # otherwise, pick based on the result_filter
            if "denominators" in url_state:
                if url_state["denominators"][0] in ["per1000", "other", "raw"]:
                    logger.info("  setting to %s", url_state["denominators"][0])
                    return url_state["denominators"][0]
                else:
                    return url_state["result_filter"]
            else:
                # default for when someone visits /apps/decile (for example)
                return "per1000"
        except NotFound:
            return "per1000"
    raise PreventUpdate


@app.callback(
    Output("denominator-tests-dropdown", "style"),
    [Input("denominators-dropdown", "value")],
)
def show_or_hide_denominators_multi_dropdown(denominators_selector):
    if denominators_selector == "other":
        return {"display": "block"}
    else:
        return {"display": "none"}


@app.callback(Output("error-container", "children"), [Input("page-state", "children")])
def show_error_from_page_state(page_state):
    """
    """
    page_state = get_state(page_state)
    if "error" in page_state:
        return [
            html.Div(
                page_state["error"]["message"],
                id="error",
                className="alert alert-danger",
            )
        ]
    else:
        return []


@app.callback(
    Output("url-for-update", "search"),
    [Input("page-state", "children")],
    [State("url-for-update", "search"), State("url-from-user", "search")],
)
def update_highlight_entities_querystring(page_state, current_qs, supplied_qs):
    page_state = get_state(page_state)
    highlight_entities = page_state.get("highlight_entities", [])
    # XXX possibly raise a NotUpdate if there's no change
    qs = "?" + urlencode(
        {"highlight_entities": highlight_entities}, doseq=True, quote_via=quote_plus
    )
    return qs


@app.callback(
    Output("org-focus-dropdown", "value"),
    [Input("heatmap-graph", "clickData"), Input("url-from-user", "search")],
    [State("page-state", "children"), State("url-for-update", "search")],
)
def update_org_focus_from_heatmap_click_or_query_string(
    heatmap_click_data, supplied_qs, page_state, current_qs
):
    """Cause the specified multi dropdown to match the current page
    location, as supplied either by the URL or by interaction with the
    heat map

    """

    page_state = get_state(page_state)
    # XXX what is current_qs any use for
    query_string = supplied_qs and urllib.parse.parse_qs(supplied_qs[1:]) or {}
    ctx = dash.callback_context
    triggered_inputs = [x["prop_id"].split(".")[0] for x in ctx.triggered]
    if "heatmap-graph" in triggered_inputs:
        # Update the URL to match the selected cell from the heatmap
        highlight_entities = page_state.get("highlight_entities", [])
        highlight_entities = toggle_entity_id_list_from_click_data(
            heatmap_click_data, highlight_entities
        )
        return highlight_entities
    elif "url-from-user" in triggered_inputs:
        return query_string.get("highlight_entities", [])


@app.callback(
    Output("org-focus-dropdown", "options"),
    [
        Input("ccg-dropdown", "value"),
        Input("lab-dropdown", "value"),
        Input("groupby-dropdown", "value"),
    ],
)
def filter_org_focus_dropdown(ccg_ids, lab_ids, groupby):
    """Reduce the organisations available in the focus dropdown to those
    within the labs or CCGs specified.

    """
    if groupby not in ["practice_id", "ccg_id", "lab_id"]:
        raise PreventUpdate
    if "all" in ccg_ids:
        ccg_ids = []
    if "all" in lab_ids:
        lab_ids = []
    return get_org_list(groupby, ccg_ids_filter=ccg_ids, lab_ids_filter=lab_ids)


@app.callback(
    [
        Output("org-filter-form", "style"),
        Output("ccg-filter-form", "style"),
        Output("lab-filter-form", "style"),
        Output("org-filter-link", "style"),
    ],
    [Input("url-from-user", "hash"), Input("page-state", "children")],
)
def toggle_org_filter_form(filter_link, page_state):
    page_state = get_state(page_state)
    ccg_ids = page_state["ccg_ids_for_practice_filter"]
    lab_ids = page_state["lab_ids_for_practice_filter"]
    groupby = page_state["groupby"]
    show = {"display": "block"}
    hide = {"display": "none"}
    if lab_ids != ["all"] and ccg_ids != ["all"] or filter_link:
        link_show = hide
        # Show at least some things in the filter form
        if groupby == "ccg_id":
            # don't allow filtering to CCG
            form_show = show
            ccg_show = hide
            lab_show = show
        elif groupby == "lab_id":
            # don't allow filtering to labs
            form_show = show
            ccg_show = show
            lab_show = hide
        elif groupby == "practice_id":
            # allow filtering to labs or CCGs
            form_show = show
            ccg_show = show
            lab_show = show
        else:
            # no filtering
            form_show = hide
            ccg_show = hide
            lab_show = hide
    else:
        link_show = show
        form_show = hide
        ccg_show = hide
        lab_show = hide
    return [form_show, ccg_show, lab_show, link_show]


# for each chart, generate a function to show only that chart
def _create_show_chart_func(chart):
    """Generate a callback function which toggles visibility of the page_id
    specified in the current page state
    """

    def show_chart(page_state):
        page_state = get_state(page_state)
        if page_state.get("page_id") == chart:
            return {"display": "block"}
        else:
            return {"display": "none"}

    return show_chart


# Register callbacks such that when the page state changes, only the
# page id currently indicated in the page state is shown
for page_id in settings.PAGES:
    app.callback(
        Output("{}-container".format(page_id), "style"),
        [Input("page-state", "children")],
    )(_create_show_chart_func(page_id))
