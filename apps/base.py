"""Callbacks that apply to all pages
"""
from data import get_test_code_to_name_map



def get_sorted_group_keys(df, group_by):
    """Compute a sort order for the practice charts, based on the mean
    calc_value of the last 6 months"""
    df2 = df.pivot_table(index=group_by, columns="month", values="calc_value")
    entity_ids = df2.reindex(
        df2.fillna(0).iloc[:, -6:].mean(axis=1).sort_values(ascending=False).index,
        axis=0,
    ).index
    return entity_ids


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


def humanise_entity_name(column_name, value):
    if column_name == "ccg_id":
        return f"CCG {value}"
    if column_name == "practice_id":
        return f"Practice {value}"
    if column_name == "test_code":
        return get_test_code_to_name_map()[value]
    if column_name == "result_category":
        return settings.ERROR_CODES[value]
    return f"{column_name} {value}"
