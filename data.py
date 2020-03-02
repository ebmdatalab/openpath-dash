import pandas as pd
from pandas.api.types import CategoricalDtype

from app import cache

import settings


@cache.memoize()
def get_data(sample_size=None):
    """Get suitably massaged data
    """
    categorical = CategoricalDtype(ordered=False)
    dtypes = {
        "ccg_id": categorical,
        "practice_id": categorical,
        "count": int,
        "error": int,
        "lab_id": categorical,
        "practice_name": categorical,
        "result_category": int,
        "test_code": categorical,
        "total_list_size": int,
    }
    df = pd.read_csv(
        settings.CSV_DIR / "all_processed.csv.zip", dtype=dtypes, parse_dates=["month"]
    )
    if sample_size:
        some_practices = df.practice_id.sample(sample_size)
        return df[df.loc[:, "practice_id"].isin(some_practices)]
    else:
        return df


@cache.memoize()
def get_practice_data():
    practice_df = read_practice_data()
    practices_with_data = get_data().practice_id.unique()
    # If we have no data for a practice at all then we don't want to include it
    # in our practice data, mainly so that its list size doesn't unfairly
    # contribute to the CCG list size
    practice_df = practice_df[practice_df.practice_id.isin(practices_with_data)]
    lab_df = get_labs_for_practices()
    practice_df = practice_df.merge(lab_df, how="left", on=["month", "practice_id"])

    return practice_df


def read_practice_data():
    categorical = CategoricalDtype(ordered=False)
    dtypes = {
        "ccg_id": categorical,
        "practice_id": categorical,
        "practice_name": categorical,
        # Even though list sizes are ints, because we have some NaN values in
        # the data (i.e. practices without a known list size) we have to use
        # floats
        "total_list_size": float,
    }
    practice_df = pd.read_csv(
        settings.CSV_DIR / "practice_codes.csv",
        dtype=dtypes,
        parse_dates=["month"],
        # We need NaN handling (see above) but we don't want to interpret
        # anything other than an empty string as NaN
        keep_default_na=False,
        na_values=[""],
    )
    practice_df = practice_df.dropna()
    return practice_df


def get_labs_for_practices():
    """
    Return a DataFrame mapping (month, practice_id) to a lab_id

    This models the fiction that each practice "belongs" to a particular lab,
    which we then use to provide a list size figure for labs to use as a
    denominator. We assign each practice to the lab where it sent the majority
    of its potassium tests, ignoring practices which sent less than 50
    potassium tests to any one lab. This implies that some practices will not
    have any associated lab in some months.

    NOTE: If we change this algorithm we should also update the text at
    /faq#lab-list-sizes
    """
    df = get_data()
    # Filter to just potassium tests and just the columns we need
    df = df[df.loc[:, "test_code"] == "K"]
    df = df[["month", "practice_id", "lab_id", "count"]]
    # Get total tests each practice sent to each lab in each month
    df = df.groupby(["month", "practice_id", "lab_id"], observed=True).sum()
    df = df.reset_index()
    # For each month and practice, keep only the lab with the highest test count
    df = df.sort_values("count", na_position="first")
    df = df.drop_duplicates(["month", "practice_id"], keep="last")
    # Filter out practices which didn't order enough tests
    df = df[df.loc[:, "count"] >= 50]
    # We no longer need this column and don't want it accidentally ending up in
    # any merges
    df = df.drop(columns=["count"])
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

    # If we're filtering the numerator to below/within/over range then we
    # filter the denominator to just numeric results, which is the ratio we're
    # generally interested in. It would be nicer not to hardcode this behaviour
    # here but it's easier to reworking the API at this stage.
    denominator_result_filter = None
    if result_filter in ("under_range", "within_range", "over_range"):
        denominator_result_filter = "numeric"

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
    result_filter_query = get_result_filter_query(result_filter)
    if result_filter_query:
        numerator_and_query.append(result_filter_query)
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
        num_df_agg = (
            filtered_df[cols_without_list_size].groupby(groupby, observed=True).sum()
        )

        practice_df = get_practice_data()

        # The easy case is when we're grouping by practice-related columns. In
        # this case we just apply the same group/sum to the practice dataframe
        # and copy the list size column across.
        if all(col in practice_df.columns for col in groupby):
            list_size_df = practice_df.groupby(groupby, observed=True).sum()
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
            list_size_df = practice_df.groupby("month", observed=True).sum()
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
    # Otherwise denominator is list of tests
    else:
        # We have two different use cases for grouping by test code when using
        # test counts as a denominator. Examples of each are:
        #
        #  1. For each of tests A, B, C show the proportion within reference
        #     range.
        #  2. For each of tests A, B, C show the count as a proportion of the
        #     total count for all A, B, C tests.
        #
        # For case 1 we want to group both the numerator and denominator
        # dataframes by month and test_code. For case 2 we want to sum the
        # denominator over all tests, which means grouping by just month rather
        # than month and test_code.
        #
        # Our API isn't rich enough to specify which we actually mean but if
        # the user supplies a result category filter and the list of numerator
        # codes is the same as the denominator codes then we can reasonably
        # infer that this is case 1. Otherwise we assume case 2.
        if by == "test_code":
            if result_filter_query and set(numerators) == set(denominators):
                # The default grouping behaviour works for this case
                pass
            else:
                # The denominator needs to be summed across all tests
                groupby = ["month"]
        denominator_and_query = base_and_query[:]
        if denominators and "all" not in denominators:
            denominator_and_query += [f"test_code.isin({denominators})"]
        denominator_filter_query = get_result_filter_query(denominator_result_filter)
        if denominator_filter_query:
            denominator_and_query.append(denominator_filter_query)
        if denominator_and_query:
            filtered_df = df.query(" & ".join(denominator_and_query))
        else:
            filtered_df = df
        denom_df_agg = (
            filtered_df[cols].groupby(groupby, observed=True).sum().reset_index()
        )
        num_df_agg = num_df_agg.merge(
            denom_df_agg,
            how="right",
            left_on=groupby,
            right_on=groupby,
            suffixes=("", "_denom"),
        )
        # Because of the right join above we may have missing numerator counts
        # on certain rows. Replace this with zeros so they still show up in the
        # final dataframe.
        num_df_agg["count"] = num_df_agg["count"].fillna(0)
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
    if not num_df_agg.empty:
        # If `by` is `None` then we're getting the raw, unaggregated data to
        # display in a table and the filtering mechanism below won't work (and
        # also, probably, is less necessary as the table will be too big to
        # parse visually in any case)
        if hide_entities_with_sparse_data and by is not None:
            # Remove all rows without data in at least 6 of the last 9 months
            num_df_agg = _filter_rows_with_sparse_data(
                num_df_agg,
                index_col=by,
                months_to_check=settings.NUM_MONTHS_TO_CHECK,
                months_required=settings.NUM_MONTHS_REQUIRED,
            )
        # The fillna is to work around this bug: https://github.com/plotly/plotly.js/issues/3296
        num_df_agg["calc_value_error"] = num_df_agg["calc_value_error"].fillna(0)
        return num_df_agg[required_cols].sort_values("month")
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


@cache.memoize()
def get_test_list():
    """Get a list of tests suitable for showing in HTML dropdown forms
    """
    df = pd.read_csv(settings.CSV_DIR / "test_codes.csv")
    df = df[["datalab_testcode", "testname"]]
    data_testcodes = get_data()["test_code"].unique()
    df = df[df["datalab_testcode"].isin(data_testcodes)]
    df = df[["datalab_testcode", "testname"]]
    df = df.rename(columns={"datalab_testcode": "value", "testname": "label"})
    df = df.sort_values("label")
    return df


@cache.memoize()
def get_test_code_to_name_map():
    df = get_test_list()
    name_map = dict(zip(df.value, df.label))
    name_map["all"] = "all tests"
    # Enforce uniqueness of test names
    inverse_map = {v: k for k, v in name_map.items()}
    if len(name_map) != len(inverse_map):
        duplicates = [v for k, v in name_map.items() if inverse_map[v] != k]
        raise ValueError(f"Non-unique test names: {', '.join(duplicates)}")
    return name_map


@cache.memoize()
def get_all_entity_ids():
    """
    Return a dict mapping entity column names to the set of all the possible
    entity_ids for that column
    """
    df = get_data()
    return {
        column_name: set(df[column_name].unique())
        for column_name in [
            "lab_id",
            "ccg_id",
            "practice_id",
            "test_code",
            "result_category",
        ]
    }


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
    data = {}
    for column_name, entity_ids in get_all_entity_ids().items():
        data.update({humanise_entity_name(column_name, k): k for k in entity_ids})
    return data


def ids_to_labels(org_type, entity_ids):
    if org_type == "lab_id":
        org_labels = [settings.LAB_NAMES.get(x, x) for x in entity_ids]
    elif org_type == "ccg_id":
        org_labels = [settings.CCG_NAMES.get(x, x) for x in entity_ids]
    elif org_type == "practice_id":
        practices = dict(
            get_practice_data().groupby(["practice_id", "practice_name"]).groups.keys()
        )
        org_labels = [practices[x] for x in entity_ids]
    return org_labels


@cache.memoize()
def get_org_list(org_type, ccg_ids_filter=None, lab_ids_filter=None):
    df = get_data()
    if ccg_ids_filter:
        df = df[df["ccg_id"].isin(ccg_ids_filter)]
    if lab_ids_filter:
        df = df[df["lab_id"].isin(lab_ids_filter)]
    org_values = df.groupby(org_type, observed=True)["test_code"].groups.keys()
    org_labels = ids_to_labels(org_type, org_values)

    org_values_and_labels = zip(org_values, org_labels)
    return [{"value": x, "label": y} for x, y in org_values_and_labels]


def humanise_entity_name(column_name, value):
    if column_name == "ccg_id":
        return f"CCG {value}"
    if column_name == "lab_id":
        return f"{settings.LAB_NAMES.get(value, value)} lab"
    if column_name == "practice_id":
        return f"Practice {value}"
    if column_name == "test_code":
        return get_test_code_to_name_map().get(value, value)
    if column_name == "result_category":
        return settings.ERROR_CODES[value]
    return f"{column_name} {value}"


def get_result_filter_query(result_filter):
    if not result_filter or result_filter == "all":
        return
    if result_filter == "within_range":
        return f"(result_category == {settings.WITHIN_RANGE})"
    elif result_filter == "under_range":
        return f"(result_category == {settings.UNDER_RANGE})"
    elif result_filter == "over_range":
        return f"(result_category == {settings.OVER_RANGE})"
    elif result_filter == "error":
        return "(result_category > 1)"
    elif result_filter == "numeric":
        return "(result_category < 2)"
    elif str(result_filter).isnumeric():
        return f"(result_category == {result_filter})"
    else:
        raise ValueError(result_filter)
