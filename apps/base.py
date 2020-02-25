"""Callbacks that apply to all pages
"""
from data import get_all_entity_ids
from data import get_test_code_to_name_map
from data import get_entity_label_to_id_map


def get_title_fragment(numerators, denominators, result_filter):
    numerators_text = humanise_test_code_list(numerators)
    if result_filter is None or result_filter == "all":
        result_filter_text = None
    else:
        result_filter_text = humanise_result_filter(result_filter)
    if result_filter_text:
        numerators_text += f" test results {result_filter_text}"
    else:
        numerators_text += " tests"
    if result_filter_text and set(numerators) == set(denominators):
        fragment = f"proportion of {numerators_text}"
    elif not denominators or denominators == ["raw"]:
        fragment = numerators_text
    elif denominators == ["per1000"]:
        fragment = f"{numerators_text} per 1000 patients"
    else:
        denominators_text = humanise_test_code_list(denominators)
        fragment = f"ratio of {numerators_text} to {denominators_text} tests"
    return fragment


def initial_capital(s):
    # Note this is distinct from `capitalize` which will lowercase the other
    # characters in the string
    return s[0:1].upper() + s[1:]


def humanise_result_filter(result_filter):
    assert result_filter is not None and result_filter != "all"
    result_filter = str(result_filter)
    if result_filter == "0" or result_filter == "within_range":
        return "within range"
    elif result_filter == "-1" or result_filter == "under_range":
        return "under range"
    elif result_filter == "1" or result_filter == "over_range":
        return "over range"
    elif result_filter == "error":
        return "with errors"
    elif result_filter == "2":
        return "with no reference range"
    elif result_filter == "3":
        return "without a numeric value"
    elif result_filter == "4":
        return "with an unknown sex"
    elif result_filter == "5":
        return "with insufficient data"
    elif result_filter == "6":
        return "where patient is underage for reference range"
    elif result_filter == "7":
        return "with an invalid reference range"
    else:
        raise ValueError(result_filter)


def humanise_test_code_list(test_codes):
    if not test_codes or "all" in test_codes or test_codes == ["None"]:
        return "all"
    test_name_map = get_test_code_to_name_map()
    test_names = [test_name_map[code] for code in test_codes]
    return humanise_list(test_names)


def humanise_list(lst):
    """
    ["a", "b", "c"] -> "a, b and c"
    """
    assert len(lst) > 0
    if len(lst) == 1:
        return lst[0]
    head = ", ".join(lst[:-1])
    tail = lst[-1]
    return f"{head} and {tail}"


def humanise_column_name(col_name, plural=True):
    s = "s" if plural else ""
    if col_name == "practice_id":
        return f"practice{s}"
    elif col_name == "ccg_id":
        return f"CCG{s}"
    elif col_name == "lab_id":
        return f"lab{s}"
    elif col_name == "test_code":
        return f"test{s}"
    elif col_name == "result_category":
        return f"result type{s}"
    else:
        raise ValueError(col_name)


def toggle_entity_id_list_from_click_data(click_data, entity_ids):
    entity_label = click_data["points"][0]["y"]
    # Hack: get the entity_id from the Y-axis label by working out the
    # labels for all entities and finding the one which matches. It ought
    # to be possible to pass the entity_id through using the `customdata`
    # property but this seems to have been broken for the last couple of
    # years. See:
    # https://community.plot.ly/t/plotly-dash-heatmap-customdata/5871
    entity_label_to_id = get_entity_label_to_id_map()
    entity_id = str(entity_label_to_id.get(entity_label, None))
    if entity_id is not None:
        if entity_id not in entity_ids:
            entity_ids.append(entity_id)
        else:
            entity_ids.remove(entity_id)
    return entity_ids


def filter_entity_ids_for_type(entity_type, entity_ids):
    valid_entity_ids = get_all_entity_ids()[entity_type]
    return [x for x in entity_ids if x in valid_entity_ids]
