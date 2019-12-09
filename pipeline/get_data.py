"""Get a list of test codes and names that have been mapped between all labs
"""
import pandas as pd
import requests

import settings
import click

from io import StringIO


CODE_MAPPINGS = {
    "nd": ["nd_testcode"],
    "cornwall": ["cornwall_testcode"],
    "plymouth": ["plym_testcode", "other_plym_codes"],
}


def get_codes():
    """Make a CSV of all the normalised test codes and lab test codes that
    have been marked in the Google Sheet for export.

    """
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSeLPEW4rTy_hCktuAXEsXtivcdREDuU7jKfXlvJ7CTEBycrxWyunBWdLgGe7Pm1A/pub?gid=241568377&single=true&output=csv"
    target_path = settings.CSV_DIR / "test_codes.csv"
    df = pd.read_csv(url, na_filter=False)
    df[df["show_in_app?"] == True].to_csv(target_path, index=False)


def get_practices():
    """Make a CSV of "standard" GP practices and list size data.
    """
    practices_url = (
        "https://openprescribing.net/api/1.0/org_code/?org_type=practice&format=csv"
    )
    target_path = settings.CSV_DIR / "practice_codes.csv"
    # For some reason delegating the URL-grabbing to pandas results in a 403
    df = pd.read_csv(StringIO(requests.get(practices_url).text), na_filter=False)
    df = df[df["setting"] == 4]
    stats_url = "https://openprescribing.net/api/1.0/org_details/?org_type=practice&keys=total_list_size&format=csv"
    df_stats = pd.read_csv(StringIO(requests.get(stats_url).text), na_filter=False)
    # Left join because we want to keep practices without populations
    # for calculating proportions
    df = df.merge(
        df_stats, left_on=["code"], right_on=["row_id"], how="left"
    ).sort_values(by=["code", "date"])
    df = df[["ccg", "code", "name", "date", "total_list_size"]]
    df.columns = ["ccg_id", "practice_id", "practice_name", "month", "total_list_size"]
    df.to_csv(target_path, index=False)


#####


def add_lab_code(df, lab_code):
    """Add a lab code for the input dataset
    """
    assert lab_code in ["nd", "cornwall", "lanc", "plymouth"]
    df["lab_id"] = lab_code
    return df


def normalise_test_codes(df, lab_code):
    """Convert local test codes into DL version
    """
    # We don't bother mapping tests that are rare, i.e. this is taken
    # into account when making the spreadsheet.
    orig_cols = df.columns
    test_code_mapping = pd.read_csv(
        settings.CSV_DIR / "test_codes.csv", na_filter=False
    )
    df["test_code"] = df["test_code"].str.strip()
    assert len(df[pd.isnull(df.test_code)]) == 0
    output = pd.DataFrame(columns=orig_cols)
    # For each test code identified for the lab in our
    # manually-curated mapping spreadsheet, rename any codes to our
    # normalised `datalab_testcode`. In addition, be sure also to
    # match on any codes in the lab data which are exactly the same as
    # the `datalab_testcode`.
    for colname in CODE_MAPPINGS[lab_code] + ["datalab_testcode"]:
        result = df.merge(
            test_code_mapping, how="inner", left_on="test_code", right_on=colname
        )
        result = result.rename(
            columns={"test_code": "source_test_code", "datalab_testcode": "test_code"}
        )
        output = output.append(result[orig_cols])
    return output[orig_cols]


def trim_practices_and_add_population(df):
    """Remove practices unlikely to be normal GP ones
    """
    # 1. Join on practices table
    # 2. Remove practices with fewer than 1000 total tests
    # 3. Remove practices that are missing population data
    practices = pd.read_csv(settings.CSV_DIR / "practice_codes.csv", na_filter=False)
    practices["month"] = pd.to_datetime(practices["month"])
    df["month"] = pd.to_datetime(df["month"])
    return df.merge(
        practices,
        how="inner",
        left_on=["month", "practice_id"],
        right_on=["month", "practice_id"],
    )


def trim_trailing_months(df):
    """There is often a lead-in to the available data. Filter out months
    which have less than 5% the max monthly test count
    """
    t2 = df.groupby(["month"])["count"].sum().reset_index().sort_values(by="count")
    t2 = t2.loc[(t2[("count")] > t2[("count")].max() * 0.05)]
    return df.merge(t2["month"].reset_index(drop=True), on="month", how="inner")


def normalise_practice_codes(df, lab_code):
    # XXX move to ND data processor
    if lab_code == "nd":
        prac = pd.read_csv(
            settings.CSV_DIR / "north_devon_practice_mapping.csv", na_filter=False
        )

        df3 = df.copy()
        df3 = df3.merge(
            prac, left_on="practice_id", right_on="LIMS code", how="inner"
        ).drop("LIMS code", axis=1)
        df3 = df3.loc[pd.notnull(df3["ODS code"])]
        df3 = df3.rename(
            columns={"practice_id": "old_practice_id", "ODS code": "practice_id"}
        ).drop("old_practice_id", axis=1)
        return df3
    else:
        return df


# Some of these should be done at data generation time, others prior
# to ingestion. For example, the anon_id stuff can happen separately
# as we don't want to run it as part of the expensive generation bits
# and it's not so sensitive


# Can be done earlier in pipeline
def estimate_errors(df):
    """Add a column indicating the "error" range for suppressed values
    """
    df["count"] = df["count"].replace("1-5", 3)
    df["count"] = df["count"].replace("1-6", 3)
    df.loc[df["count"] == 3, "error"] = 2
    df["error"] = df["error"].fillna(0)
    df["count"] = pd.to_numeric(df["count"])
    return df


def anonymise(df):
    df["practice_id"] = df.groupby("practice_id").ngroup()
    df["practice_name"] = df["practice_id"].astype(str) + " SURGERY"
    return df


def report_oddness(df):
    report = (
        df.query("result_category > 1")
        .groupby(["test_code", "lab_id", "result_category"])
        .count()
        .reset_index()[["result_category", "lab_id", "test_code", "month"]]
    )
    denominators = (
        df.groupby(["test_code", "lab_id"])
        .count()
        .reset_index()[["lab_id", "test_code", "month"]]
    )
    report = report.merge(
        denominators,
        how="inner",
        left_on=["test_code", "lab_id"],
        right_on=["test_code", "lab_id"],
    )
    report["percentage"] = report["month_x"] / report["month_y"]
    report["result_category"] = report["result_category"].replace(settings.ERROR_CODES)
    odd = report[report["percentage"] > 0.1]
    if len(odd):
        print("The following error codes are more than 10% of all the results:")
        print()
        with pd.option_context("display.max_rows", None, "display.max_columns", None):
            print(odd[["result_category", "test_code", "lab_id", "percentage"]])


@click.argument("lab_code")
@click.argument("filename")
def process_file(lab_code, filename):
    df = pd.read_csv(filename, na_filter=False)
    df = add_lab_code(df, lab_code)
    df = normalise_test_codes(df, lab_code)
    df = normalise_practice_codes(df, lab_code)
    df = estimate_errors(df)  # XXX can do this earlier in the pipeline
    df = trim_trailing_months(df)
    df = trim_practices_and_add_population(df)
    df = df[
        [
            "ccg_id",
            "count",
            "error",
            "lab_id",
            "month",
            "practice_id",
            "practice_name",
            "result_category",
            "test_code",
            "total_list_size",
        ]
    ]
    df.to_csv(settings.CSV_DIR / f"{lab_code}_processed.csv", index=False)


@click.argument("filenames", nargs=-1)
def postprocess_files(filenames):
    df = pd.DataFrame()
    for filename in filenames:
        if not filename.endswith("/all_processed.csv"):
            df = pd.concat([df, pd.read_csv(filename, na_filter=False)], sort=False)
    # df = anonymise(df)
    report_oddness(df)
    df.to_csv(settings.CSV_DIR / f"all_processed.csv", index=False)
