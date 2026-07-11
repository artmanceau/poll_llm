import polars as pl


MONTHS = {
    "janvier": 1,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
}


def parse_poll_dates(
    df: pl.DataFrame,
    year: int,
) -> pl.DataFrame:

    df = df.with_columns(
        pl.col("Dates")
        .str.to_lowercase()
        .str.replace_all("\u00a0", " ")
        .str.replace_all("1er", "1")
        .alias("date_clean")
    )

    df = df.with_columns(

        pl.col("date_clean")
        .str.extract(
            r"(\d+)\s*([a-zéû]+)\s*$",
            1,
        )
        .cast(pl.Int32)
        .alias("day"),

        pl.col("date_clean")
        .str.extract(
            r"(\d+)\s*([a-zéû]+)\s*$",
            2,
        )
        .alias("month_name"),

    )


    df = df.with_columns(
        pl.col("month_name")
        .replace(MONTHS)
        .cast(pl.Int32)
        .alias("month")
    )


    df = df.with_columns(
        pl.datetime(
            year,
            pl.col("month"),
            pl.col("day"),
        )
        .alias("date")
    )


    df = df.with_columns(
        (
            pl.col("month")
            >
            pl.col("month").shift(1)
        )
        .fill_null(False)
        .cast(pl.Int32)
        .cum_sum()
        .alias("year_offset")
    )


    df = df.with_columns(
        pl.col("date")
        .dt.offset_by(
            (-pl.col("year_offset"))
            .cast(pl.String)
            + "y"
        )
        .alias("date")
    )

    return df