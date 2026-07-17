import polars as pl


def add_source(
    df: pl.DataFrame,
    source: str,
):

    return df.with_columns(
        pl.lit(source)
        .alias("source")
    )


def prepare_comparison_df(
    resume,
    official,
    year,
):
    return pl.concat(
        [
            resume
            .select(
                [
                    f"vote{year}",
                    "pvote",
                ]
            )
            .pipe(
                add_source,
                "LLM poll",
            ),
            official
        ]
    )