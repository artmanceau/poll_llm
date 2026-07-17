import polars as pl
import plotly.graph_objects as go

from config import (
    CANDIDATE_TO_BLOC,
    BLOC_COLORS,
    SOURCE_PATTERNS,
    build_bar_colors,
)


BAR_COLORS = build_bar_colors()


def aggregate_blocs(
    df: pl.DataFrame,
    year: int,
):

    return (
        df
        .with_columns(
            pl.col(f"vote{year}")
            .replace(CANDIDATE_TO_BLOC)
            .alias("bloc")
        )
        .group_by(
            [
                "bloc",
                "source",
            ]
        )
        .agg(
            pl.col("pvote")
            .sum()
        )
    )


def global_bar_plot(
    df: pl.DataFrame,
    year: int,
):

    fig = go.Figure()

    for source in df["source"].unique():

        pdf = (
            df
            .filter(
                pl.col("source")
                ==
                source
            )
            .to_pandas()
        )

        fig.add_trace(
            go.Bar(
                x=pdf[f"vote{year}"],
                y=pdf["pvote"],
                name=source,
                text=pdf["pvote"],
                texttemplate="%{y:.1f}%",
                textposition="outside",
                marker=dict(
                    color=[
                        BAR_COLORS[
                            (
                                candidate,
                                source,
                            )
                        ]
                        for candidate
                        in pdf[f"vote{year}"]
                    ],
                    pattern=dict(
                        shape=SOURCE_PATTERNS[source],
                        solidity=0.3,
                    ),
                ),
            )
        )

    fig.update_layout(
        barmode="group",
        height=600,
        xaxis_title="Candidat",
        yaxis_title="Score (%)",
        legend_title="Source",
    )

    return fig


def bloc_bar_plot(
    df: pl.DataFrame,
):

    fig = go.Figure()

    for source in df["source"].unique():

        pdf = (
            df
            .filter(
                pl.col("source")
                ==
                source
            )
            .to_pandas()
        )


        fig.add_trace(
            go.Bar(
                x=pdf["bloc"],
                y=pdf["pvote"],
                name=source,
                text=pdf["pvote"],
                texttemplate="%{y:.1f}%",
                textposition="outside",
                marker=dict(
                    color=[
                        BLOC_COLORS[x]
                        for x in pdf["bloc"]
                    ],
                    pattern=dict(
                        shape=SOURCE_PATTERNS[source],
                        solidity=0.3,
                    ),
                ),
            )
        )


    fig.update_layout(
        barmode="group",
        height=500,
        xaxis_title="Bloc",
        yaxis_title="Score (%)",
    )

    return fig