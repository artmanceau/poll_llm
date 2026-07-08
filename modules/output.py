import polars as pl


def save(df, path):

    df.write_parquet(
        path
    )


def summary(df):

    return (
        df
        .group_by("vote")
        .agg(
            pl.len()
            .alias("respondents"),
            pl.sum("weight")
            .alias("weighted_share")
        )
        .sort(
            "respondents",
            descending=True
        )
    )