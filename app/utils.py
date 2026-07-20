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
    resume_wo_abstention = resume.filter(~(pl.col(f'vote{year}').is_in(['Abstention', 'Non inscrit', 'Vote blanc ou nul'])))
    n_vote = resume_wo_abstention.select('vote').sum().item()
    resume_wo_abstention = resume_wo_abstention.with_columns(
        pvote=(pl.col('vote') / n_vote) * 100
    )
    return pl.concat(
        [
            resume_wo_abstention
            .select(
                [
                    f"vote{year}",
                    'pvote'
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
):
    """Per model run, bias vs the official result on Total Gauche / Total
    Droite and the mean absolute error across candidates.

    bias = LLM share - official share (in points). Positive TG bias means the
    model over-estimates the left.
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