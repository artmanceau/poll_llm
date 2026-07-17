import polars as pl

from config import CANDIDATE_TO_SIDE


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


def compute_bias(
    all_summaries,
    official,
    year,
    normalize=True,
):
    """Per model run, bias vs the official result on Total Gauche / Total
    Droite and the mean absolute error across candidates.

    bias = LLM share - official share (in points). Positive TG bias means the
    model over-estimates the left. When ``normalize`` is set, LLM candidate
    shares are rescaled to expressed votes (abstention/blank dropped) so both
    sides are shares of the same base as the official result.
    """

    vote_col = f"vote{year}"

    off = (
        official
        .select([vote_col, "pvote"])
        .rename({"pvote": "pvote_off"})
    )

    official_candidates = off[vote_col].to_list()

    rows = []

    for keys, grp in all_summaries.group_by(
        ["version", "model", "respondents"],
        maintain_order=True,
    ):

        version, model, respondents = keys

        cand = grp.filter(
            pl.col(vote_col).is_in(official_candidates)
        )

        if normalize:
            total = cand["pvote"].sum()
            if total and total > 0:
                cand = cand.with_columns(
                    (pl.col("pvote") / total * 100).alias("pvote")
                )

        merged = (
            cand
            .join(off, on=vote_col, how="inner")
            .with_columns(
                pl.col(vote_col)
                .replace_strict(
                    CANDIDATE_TO_SIDE,
                    default=None,
                )
                .alias("side")
            )
        )

        if merged.is_empty():
            continue

        tg = merged.filter(pl.col("side") == "TG")
        td = merged.filter(pl.col("side") == "TD")

        rows.append(
            {
                "version": version,
                "model": model,
                "respondents": respondents,
                "tg_bias": tg["pvote"].sum() - tg["pvote_off"].sum(),
                "td_bias": td["pvote"].sum() - td["pvote_off"].sum(),
                "avg_error": (
                    (merged["pvote"] - merged["pvote_off"])
                    .abs()
                    .mean()
                ),
            }
        )

    return pl.DataFrame(rows)