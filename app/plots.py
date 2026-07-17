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


def bias_scatter(
    df: pl.DataFrame,
):
    """Scatter of each LLM run: x = Total Gauche bias, y = Total Droite bias,
    marker color = mean absolute error across candidates."""

    pdf = df.to_pandas()

    text = [
        f"{m} (n={r}), version {v}"
        for m, r, v in zip(pdf["model"], pdf["respondents"], pdf['version'])
    ]

    customdata = pdf[
        ["version", "model", "respondents", "avg_error"]
    ].to_numpy()

    span = max(
        1.0,
        float(
            pdf[["tg_bias", "avg_error"]]
            .abs()
            .to_numpy()
            .max()
        ),
    ) * 1.15

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=pdf["tg_bias"],
            y=pdf["avg_error"],
            mode="markers+text",
            text=text,
            textposition="top center",
            marker=dict(
                size=16,
                color=pdf["respondents"],
                colorscale="Reds",
                showscale=True,
                colorbar=dict(
                    title="Respondents"
                ),
                line=dict(width=1, color="#333333"),
            ),
            customdata=customdata,
            hovertemplate=(
                "<b>%{customdata[1]}</b><br>"
                "Version : %{customdata[0]}<br>"
                "Répondants : %{customdata[2]}<br>"
                "Biais en faveur de la droite (%) : %{x:.1f} pts<br>"
                "Erreur moyenne (tous les candidats): %{y:.1f} pts"
                "<extra></extra>"
            ),
        )
    )

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="grey",
    )
    fig.add_vline(
        x=0,
        line_dash="dash",
        line_color="grey",
    )

    fig.update_layout(
        height=650,
        xaxis_title="Biais en faveur de la droite (%)",
        yaxis_title="Erreur moyenne (tous les candidats)",
        xaxis=dict(range=[-span, span], zeroline=False),
        yaxis=dict(range=[0, span], zeroline=False),
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