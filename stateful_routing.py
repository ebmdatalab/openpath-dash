"""This module is responsible for maintaining state for the user, and
ensuring this state is also reflected in the URL.

The state is stored as stringified JSON stored in a hidden div.

"""
import json
import urllib
import logging
import dash
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_html_components as html
import dash_core_components as dcc

from app import app
from werkzeug.routing import NotFound
from werkzeug.routing import BuildError
from urls import url_map
from urls import urls
from data import get_measures


logger = logging.getLogger(__name__)


def get_state(possible_state_text):
    """Get state from stringifyed JSON, or an empty dict
    """
    try:
        state = json.loads(possible_state_text)
    except (json.decoder.JSONDecodeError, TypeError):
        state = {}
    return state


def update_state(state, **kw):
    """Update `state` with keyword values, if they are different from
    current values, and non-null. Keyword values of None or empty
    lists denote that the key should be removed from the state.

    Sets a `_dirty` key if any changes have been made

    """
    changed = False
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
            changed = True
    if changed:
        state["_dirty"] = True


def _url_from_state(page_state):
    url = None
    # Find the last rule (`iter_rules` iterates over the map in
    # reverse order) that can match our state
    for endpoint in [x.endpoint for x in url_map.iter_rules()]:
        try:
            logger.debug("  trying endpoint %s for state %s", endpoint, page_state)
            url = urls.build(endpoint, page_state, append_unknown=False)
            logger.debug("Found url %s", url)
            # Now add the rest to the query string
            url = urls.build(endpoint, page_state, append_unknown=True)
            break
        except BuildError:
            pass
    if not url:
        logger.debug("No url found for state %s; PreventUpdate", page_state)
        raise PreventUpdate
    return url


@app.callback(Output("url-for-update", "pathname"), [Input("page-state", "children")])
def update_url_from_page_state(page_state):
    """Cause the page location to match the current page state
    """
    page_state = get_state(page_state)
    logger.debug("Getting URL from page state %s", page_state)
    return _url_from_state(page_state)


@app.callback(
    Output("page-state", "children"),
    [
        Input("heatmap-graph", "clickData"),
        Input("numerators-dropdown", "value"),
        Input("denominators-dropdown", "value"),
        Input("denominator-tests-dropdown", "value"),
        Input("groupby-dropdown", "value"),
        Input("test-filter-dropdown", "value"),
        Input("ccg-dropdown", "value"),
        Input("chart-selector-tabs", "active_tab"),
        Input("tweak-form", "value"),
    ],
    [
        State("page-state", "children"),
        State("url-for-update", "pathname"),
        State("url-for-update", "search"),
    ],
)
def update_state_from_inputs(
    click_data,
    selected_numerator,
    selected_denominator,
    denominator_tests,
    groupby,
    selected_filter,
    selected_ccg,
    selected_chart,
    tweak_form,
    page_state,
    current_path,
    current_qs,
):
    """
    Given a series of possible user inputs, update the state if it needs to be changed.
    """
    ctx = dash.callback_context
    triggered_inputs = [x["prop_id"].split(".")[0] for x in ctx.triggered]
    page_state = get_state(page_state)
    orig_page_state = page_state.copy()
    query_string = urllib.parse.parse_qs(current_qs[1:])
    # add defaults
    if "numerators" not in page_state:
        update_state(page_state, numerators=["K"])
    if "denominators" not in page_state:
        update_state(page_state, denominators=["per1000"])
    if "groupby" not in page_state:
        update_state(page_state, groupby="practice_id")
    if "practice_filter_entity" not in page_state:
        update_state(page_state, practice_filter_entity="ccg_id")
    if "entity_ids_for_practice_filter" not in page_state:
        update_state(page_state, entity_ids_for_practice_filter=["all"])
    if "result_filter" not in page_state:
        update_state(page_state, result_filter="all")

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
        entity_ids_for_practice_filter=selected_ccg,
        highlight_entities=query_string.get("highlight_entities", []),
        page_id=selected_chart,
        sparse_data_toggle=sparse_data_toggle,
        equalise_colorscale=equalise_colorscale,
    )

    if "heatmap-graph" in triggered_inputs:
        # Hack: extract practice id from chart label data, which looks
        # like this: {'points': [{'curveNumber': 0, 'x': '2016-05-01',
        # 'y': 'practice 84', 'z': 86.10749488t62395}]}. I think
        # there's a cleaner way to pass ids as chart metadata
        entity_id = click_data["points"][0]["y"].split(" ")[-1]
        highlights = page_state.get("highlight_entities", [])
        highlights.append(entity_id)
        update_state(page_state, highlight_entities=highlights)

    # Only trigger state changes if something has changed
    if "_dirty" not in page_state:
        logger.info("State unchanged")
        raise PreventUpdate

    del page_state["_dirty"]
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
            return component.value[0]
        else:
            return component.options[0]["value"]
    else:
        return ""


def _create_dropdown_update_func(selector_id, page_state_key, is_multi):
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
                return is_multi and [current_value] or current_value
        raise PreventUpdate

    return update_dropdown_from_url


def _create_link_update_func(selector_id):
    """Create a callback function that updates a dropdown from a URL
    """

    def update_link_from_state(page_state):
        """Substitute page_id in a given link with that found in the page_state
        """
        page_state = get_state(page_state)
        page_state["page_id"] = selector_id
        return _url_from_state(page_state)

    return update_link_from_state


for selector_id, page_state_key, is_multi in [
    ("numerators-dropdown", "numerators", True),
    ("denominator-tests-dropdown", "denominators", True),
    ("test-filter-dropdown", "result_filter", False),
    ("groupby-dropdown", "groupby", False),
    ("ccg-dropdown", "entity_ids_for_practice_filter", True),
]:
    app.callback(Output(selector_id, "value"), [Input("url-from-user", "pathname")])(
        _create_dropdown_update_func(selector_id, page_state_key, is_multi)
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
            return url_state["page_id"]
        except NotFound:
            return ""
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
            if "denominators" in url_state:
                if url_state["denominators"] == ["per1000"] or url_state[
                    "denominators"
                ] == ["raw"]:
                    logger.info("  setting to %s", url_state["denominators"][0])
                    return url_state["denominators"][0]
                else:
                    return "other"
            else:
                # default for when someone visits /apps/decile (for example)
                return "per1000"
        except NotFound:
            return ""
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
    Output("description-container", "children"), [Input("url-from-user", "search")]
)
def show_measure_description_from_url(search):
    """
    """
    if search and "id" in search:
        measure_id = urllib.parse.parse_qs(search[1:])["id"][0]
        measures = get_measures()
        measure = measures[measures["id"] == measure_id].to_dict("records")[0]
        return [
            dcc.Markdown(
                f"## {measure['title']}\n\n{measure['description']}",
                className="alert alert-info",
            )
        ]
    else:
        return []
