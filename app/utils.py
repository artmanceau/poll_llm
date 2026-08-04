import polars as pl
import os
from config import candidate_to_side


def add_source(
    df: pl.DataFrame,
    source: str,
):
    return df.with_columns(pl.lit(source).alias("source"))


def prepare_comparison_df(
    resume,
    official,
    year,
):
    if official.is_empty():
        return resume.select([f"vote{year}", "pvote"]).pipe(
            add_source,
            "LLM poll",
        )
    else:
        return pl.concat(
            [
                resume.select([f"vote{year}", "pvote"]).pipe(
                    add_source,
                    "LLM poll",
                ),
                official,
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

    off = official.select([vote_col, "pvote"]).rename({"pvote": "pvote_off"})

    official_candidates = off[vote_col].to_list()

    rows = []

    for keys, grp in all_summaries.group_by(
        ["version", "model", "respondents"],
        maintain_order=True,
    ):
        version, model, respondents = keys

        cand = grp.unique().filter(pl.col(vote_col).is_in(official_candidates))

        total = cand["pvote"].sum()
        if total and total > 0:
            cand = cand.with_columns((pl.col("pvote") / total * 100).alias("pvote"))

        merged = cand.join(off, on=vote_col, how="outer", coalesce=True).with_columns(
            pl.col(vote_col)
            .replace_strict(
                candidate_to_side(year),
                default=None,
            )
            .alias("side")
        )

        if merged.is_empty():
            continue

        tg = merged.filter(pl.col("side") == "TG")
        td = merged.filter(pl.col("side") == "TD")
        c = merged.filter(pl.col("side") == "C")
        tg_poll = tg["pvote"].sum() + c["pvote"].sum() / 2
        td_poll = td["pvote"].sum() + c["pvote"].sum() / 2
        tg_off = tg["pvote_off"].sum() + c["pvote_off"].sum() / 2
        td_off = td["pvote_off"].sum() + c["pvote_off"].sum() / 2

        rows.append(
            {
                "version": version,
                "model": model,
                "respondents": respondents,
                "tg_bias": tg_poll - tg_off,
                "td_bias": td_poll - td_off,
                "avg_error": ((merged["pvote"] - merged["pvote_off"]).abs().mean()),
            }
        )

    return pl.DataFrame(rows)


def clean_env_var():
    for key in [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_PROFILE",
        "AWS_SHARED_CREDENTIALS_FILE",
        "AWS_CONFIG_FILE",
        "AWS_WEB_IDENTITY_TOKEN_FILE",
    ]:
        os.environ.pop(key, None)
