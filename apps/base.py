"""Callbacks that apply to all pages
"""
from dash.dependencies import Input, Output

from app import app
from stateful_routing import get_state
import settings
from data import get_test_code_to_name_map


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


def get_sorted_group_keys(df, group_by):
    """Compute a sort order for the practice charts, based on the mean
    calc_value of the last 6 months"""
    df2 = df.pivot_table(index=group_by, columns="month", values="calc_value")
    entity_ids = df2.reindex(
        df2.fillna(0).iloc[:, -6:].mean(axis=1).sort_values(ascending=False).index,
        axis=0,
    ).index
    return entity_ids


def get_chart_title(numerators, denominators, result_filter, entity_names):

    # Make a title

    # Function giving a test's name from its code
    get_test_name = get_test_code_to_name_map().__getitem__

    if not numerators or "all" in numerators:
        numerators_text = "all tests"
    else:
        numerators_text = " + ".join(map(get_test_name, numerators))
    if not denominators:
        denominators_text = "(raw numbers)"
    elif denominators == ["per1000"]:
        denominators_text = "per 1000 patients"
    else:
        denominators_text = "as a proportion of " + " + ".join(
            map(get_test_name, denominators)
        )
    filter_text = ""  # XXX <- this needs to include under range , over range, etc
    if entity_names:
        entity_names = " + ".join(map(str, entity_names))
        title = "Number of {} {} at {}{}".format(
            numerators_text, denominators_text, entity_names, filter_text
        )
    else:
        title = "Global deciles of {} {}{} ".format(
            numerators_text, denominators_text, filter_text
        )

    return title


def humanise_entity_name(column_name, value):
    if column_name == "ccg_id":
        return f"CCG {value}"
    if column_name == "practice_id":
        return f"Practice {value}"
    if column_name == "test_code":
        return get_test_code_to_name_map()[value]
    if column_name == "result_category":
        return settings.ERROR_CODES_SHORT[value]
    return f"{column_name} {value}"
