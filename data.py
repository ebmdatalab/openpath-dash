import pandas as pd
from app import cache

import settings


@cache.memoize()
def get_data(sample_size=None):
    """Get suitably massaged data
    """
    df = pd.read_csv(
        settings.CSV_DIR / "all_processed.csv.zip",
        dtype={"ccg_id": str, "practice_id": str},
    )

    # Convert month to datetime
    df.loc[:, "month"] = pd.to_datetime(df["month"])

    if sample_size:
        some_practices = df.practice_id.sample(sample_size)
        return df[df.loc[:, "practice_id"].isin(some_practices)]
    else:
        return df


@cache.memoize()
def get_count_data(
    numerators=[],
    denominators=[],
    result_filter=None,
    lab_ids_for_practice_filter=[],
    ccg_ids_for_practice_filter=[],
    by="practice_id",
    sample_size=None,
    hide_entities_with_sparse_data=False,
):
    """Get anonymised count data (for all categories) by month and test_code and practice
    """
    df = get_data(sample_size)
    if by == "practice_id":
        cols = ["month", "total_list_size", "practice_id", "ccg_id", "count", "error"]
        groupby = ["month", "practice_id", "ccg_id"]
        required_cols = [
            "month",
            "total_list_size",
            "practice_id",
            "numerator",
            "denominator",
            "label",
            "calc_value",
            "calc_value_error",
            "ccg_id",
        ]
    # XXX how do we do this.
    # We group by X, then do calc-value; but what about the percentiles?
    elif by == "test_code":
        cols = ["month", "test_code", "count", "error", "total_list_size"]
        groupby = ["month", "test_code"]
        required_cols = [
            "month",
            "test_code",
            "calc_value",
            "calc_value_error",
            "label",
            "numerator",
            "denominator",
        ]
    elif by == "result_category":
        cols = ["month", "result_category", "count", "error", "total_list_size"]
        groupby = ["month", "result_category"]
        required_cols = [
            "month",
            "result_category",
            "calc_value",
            "calc_value_error",
            "label",
            "numerator",
            "denominator",
        ]
    elif by == "ccg_id":
        cols = ["month", "total_list_size", "ccg_id", "count", "error"]
        groupby = ["month", "ccg_id"]
        required_cols = [
            "month",
            "total_list_size",
            "label",
            "numerator",
            "denominator",
            "ccg_id",
            "calc_value",
            "calc_value_error",
        ]
    elif by == "lab_id":
        cols = ["month", "total_list_size", "lab_id", "count", "error"]
        groupby = ["month", "lab_id"]
        required_cols = [
            "month",
            "total_list_size",
            "label",
            "numerator",
            "denominator",
            "lab_id",
            "calc_value",
            "calc_value_error",
        ]
    elif not by:
        cols = [
            "month",
            "test_code",
            "result_category",
            "calc_value",
            "calc_value_error",
            "practice_id",
            "ccg_id",
            "total_list_size",
        ]
        required_cols = cols + [
            "label",
            "numerator",
            "numerator_error",
            "denominator",
            "denominator_error",
        ]

        groupby = None
    base_and_query = []
    if lab_ids_for_practice_filter and "all" not in lab_ids_for_practice_filter:
        base_and_query.append(f"(lab_id.isin({lab_ids_for_practice_filter}))")
    if ccg_ids_for_practice_filter and "all" not in ccg_ids_for_practice_filter:
        base_and_query.append(f"(ccg_id.isin({ccg_ids_for_practice_filter}))")
    numerator_and_query = base_and_query[:]
    if result_filter:
        if result_filter == "within_range":
            numerator_and_query.append(f"(result_category == {settings.WITHIN_RANGE})")
        elif result_filter == "under_range":
            numerator_and_query.append(f"(result_category == {settings.UNDER_RANGE})")
        elif result_filter == "over_range":
            numerator_and_query.append(f"(result_category == {settings.OVER_RANGE})")
        elif result_filter == "error":
            numerator_and_query.append("(result_category > 1)")
        elif str(result_filter).isnumeric():
            numerator_and_query.append(f"(result_category == {result_filter})")

    if numerators and numerators != ["all"]:
        numerator_and_query += [f"(test_code.isin({numerators}))"]
    if numerator_and_query:
        filtered_df = df.query(" & ".join(numerator_and_query))
    else:
        filtered_df = df
    if groupby:
        # Because each practice-month pair might occur multiple times in our
        # dataframe (once for each test code and result category) we can't
        # simply sum the `total_list_size` column as this will end up counting
        # the same list size value multiple times. So we handle this
        # separately.
        cols_without_list_size = [c for c in cols if c != "total_list_size"]
        num_df_agg = filtered_df[cols_without_list_size].groupby(groupby).sum()

        # First we construct a dataframe which contains practice details with
        # exactly one entry for each practice-month pair.
        practice_df = df[
            ["month", "practice_id", "ccg_id", "lab_id", "total_list_size"]
        ]
        practice_df = practice_df.drop_duplicates(["month", "practice_id"])

        # The easy case is when we're grouping by practice-related columns. In
        # this case we just apply the same group/sum to the practice dataframe
        # and copy the list size column across.
        if all(col in practice_df.columns for col in groupby):
            list_size_df = practice_df.groupby(groupby).sum()
            num_df_agg.loc[:, "total_list_size"] = list_size_df["total_list_size"]
            num_df_agg = num_df_agg.reset_index()

        # The more complex case is where we're grouping by something not
        # practice-related e.g. test_code.  In this case we calculate a total
        # list size for each month and copy that value across using a merge.
        else:
            # If we're filtering by CCG or Lab then we need to apply that
            # filter here otherwise we'll get the national total list size
            # rather than the total for just the selected CCG/Lab.
            if base_and_query:
                practice_df = practice_df.query(" & ".join(base_and_query))
            list_size_df = practice_df.groupby("month").sum()
            num_df_agg = num_df_agg.reset_index()
            num_df_agg = num_df_agg.merge(
                list_size_df, left_on="month", right_index=True
            )
    else:
        num_df_agg = filtered_df
    if denominators == ["per1000"]:
        num_df_agg.loc[:, "denominator"] = num_df_agg["total_list_size"]
        num_df_agg.loc[:, "denominator_error"] = num_df_agg["error"]
        num_df_agg.loc[:, "calc_value"] = (
            num_df_agg["count"] / num_df_agg["total_list_size"] * 1000
        )
        num_df_agg.loc[:, "calc_value_error"] = (
            num_df_agg["error"] / num_df_agg["total_list_size"] * 1000
        )
        label_format = (
            "{0[calc_value]:.5f} "
            "({0[numerator]:.0f} tests per {0[denominator]:.0f} patients)"
        )
    elif denominators == ["raw"]:
        num_df_agg.loc[:, "denominator"] = num_df_agg["count"]
        num_df_agg.loc[:, "denominator_error"] = num_df_agg["error"]
        num_df_agg.loc[:, "calc_value"] = num_df_agg["count"]
        num_df_agg.loc[:, "calc_value_error"] = num_df_agg["error"]
        label_format = "{0[numerator]:.0f} tests"
    else:
        # denominator is list of tests
        if by == "test_code":
            # The denominator needs to be summed across all tests
            groupby = ["month"]
        denominator_and_query = base_and_query[:]
        if denominators and "all" not in denominators:
            denominator_and_query += [f"test_code.isin({denominators})"]
        if denominator_and_query:
            filtered_df = df.query(" & ".join(denominator_and_query))
        else:
            filtered_df = df
        denom_df_agg = filtered_df[cols].groupby(groupby).sum().reset_index()
        num_df_agg = num_df_agg.merge(
            denom_df_agg,
            how="right",
            left_on=groupby,
            right_on=groupby,
            suffixes=("", "_denom"),
        )
        num_df_agg.loc[:, "calc_value"] = (
            num_df_agg["count"] / num_df_agg["count_denom"]
        )
        num_df_agg.loc[:, "calc_value_error"] = (
            num_df_agg["error"] / num_df_agg["count_denom"]
        )
        num_df_agg = num_df_agg.rename(
            columns={"count_denom": "denominator", "error_denom": "denominator_error"}
        )
        label_format = (
            "{0[calc_value]:.5f} ({0[numerator]:.0f} / {0[denominator]:.0f} tests)"
        )
    num_df_agg = num_df_agg.rename(
        columns={"count": "numerator", "error": "numerator_error"}
    )
    # Always include date in label
    label_format += " in {0[month]:%b %Y}"
    num_df_agg["label"] = num_df_agg.apply(label_format.format, axis=1)
    # If `by` is `None` then we're getting the raw, unaggregated data to display in a table
    # and the filtering mechanism below won't work (and also, probably, is less necessary as
    # the table will be too big to parse visually in any case)
    if not num_df_agg.empty:
        if hide_entities_with_sparse_data and by is not None:
            # Remove all rows without data in at least 6 of the last 9 months
            num_df_agg = _filter_rows_with_sparse_data(
                num_df_agg,
                index_col=by,
                months_to_check=settings.NUM_MONTHS_TO_CHECK,
                months_required=settings.NUM_MONTHS_REQUIRED,
            )
        # The fillname is to work around this bug: https://github.com/plotly/plotly.js/issues/3296
        return num_df_agg[required_cols].sort_values("month").fillna(0)
    else:
        return pd.DataFrame()


def _filter_rows_with_sparse_data(df, index_col, months_to_check, months_required):
    recent_months = sorted(df.month.unique())
    months_to_check = min(len(recent_months), months_to_check)
    recent_months_cutoff = recent_months[-months_to_check]
    recent_data = df[df.month >= recent_months_cutoff]
    recent_data_by_month = recent_data.pivot(
        index=index_col, columns="month", values="calc_value"
    )
    remaining_ids = recent_data_by_month.dropna(thresh=months_required).index
    return df[df[index_col].isin(remaining_ids)]


def get_test_list():
    """Get a list of tests suitable for showing in HTML dropdown forms
    """
    df = pd.read_csv(settings.CSV_DIR / "test_codes.csv")
    df = df[["datalab_testcode", "testname"]]
    df = df.rename(columns={"datalab_testcode": "value", "testname": "label"})
    return df


@cache.memoize()
def get_test_code_to_name_map():
    df = get_test_list()
    name_map = dict(zip(df.value, df.label))
    name_map["all"] = "all tests"
    return name_map


@cache.memoize()
def get_entity_label_to_id_map():
    """Return a dict of labels to ids. Required for interaction between
    deciles and heatmap charts

    """
    # Hack: get the entity_id from the Y-axis label by working out the
    # labels for all entities and finding the one which matches. It ought
    # to be possible to pass the entity_id through using the `customdata`
    # property but this seems to have been broken for the last couple of
    # years. See:
    # https://community.plot.ly/t/plotly-dash-heatmap-customdata/5871

    column_names = ["lab_id", "ccg_id", "practice_id", "test_code", "result_category"]
    data = {}
    for column_name in column_names:
        keys = get_data()[column_name].unique()
        data.update({humanise_entity_name(column_name, k): k for k in keys})
    return data


@cache.memoize()
def get_ccg_list():
    """Get data suitably massaged for use in a dropdown
    """
    return [
        {"value": x, "label": x}
        for x in get_data().groupby("ccg_id")["test_code"].groups.keys()
    ]


@cache.memoize()
def get_lab_list():
    """Get data suitably massaged for use in a dropdown
    """
    return [
        {"value": x, "label": x}
        for x in get_data().groupby("lab_id")["test_code"].groups.keys()
    ]


def humanise_entity_name(column_name, value):
    if column_name == "ccg_id":
        return f"CCG {value}"
    if column_name == "lab_id":
        return f"{settings.LAB_NAMES[value]} lab"
    if column_name == "practice_id":
        return f"Practice {value}"
    if column_name == "test_code":
        return get_test_code_to_name_map()[value]
    if column_name == "result_category":
        return settings.ERROR_CODES[value]
    return f"{column_name} {value}"
