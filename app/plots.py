import numpy as np
import pandas as pd
import polars as pl
import streamlit as st
import plotly.graph_objects as go

from statsmodels.nonparametric.smoothers_lowess import lowess

from config import (
    CANDIDATES,
    CANDIDATE_COLORS,
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


def poll_evolution_plot(
    polls,
    official,
    year,
    mode="candidate",
):

    fig = go.Figure()

    st.write(polls)

    sondeur = st.multiselect('Sondeur', polls.unique('Sondeur').get_column('Sondeur').to_list(), default=polls.unique('Sondeur').get_column('Sondeur').to_list())
    min_echantillon, max_echantillon = st.slider("Taille de l'échantillon",  polls.get_column('Échantillon').min(), polls.get_column('Échantillon').max(), (polls.get_column('Échantillon').min(), polls.get_column('Échantillon').max()))
    min_date, max_date = st.slider("Date du sondage",  polls.get_column('date').min(), polls.get_column('date').max(), (polls.get_column('date').min(), polls.get_column('date').max()))

    if mode == "candidate":

        items = CANDIDATES

        colors = CANDIDATE_COLORS

        columns = CANDIDATES


    else:

        items = list(
            BLOC_COLORS.keys()
        )

        colors = BLOC_COLORS


        polls = (
            polls
            .with_columns(
                [
                    (
                        sum(
                            [
                                pl.col(c)
                                for c in candidates
                            ]
                        )
                    )
                    .alias(bloc)
                    for bloc, candidates
                    in _bloc_columns().items()
                ]
            )
        )
        official = (
            official
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
                .alias("pvote")
            )
            .rename(
                {
                    "bloc": f"vote{year}"
                }
            )
        )
        columns = items



    for item in items:
        
        true_score = (
            official
            .filter(pl.col(f"vote{year}") == item)
            .select("pvote")
            .item()
        )

        fig.add_hline(
            y=true_score,
            line_width=2,
            line_dash='longdash',
            line_color=colors[item],
            annotation_text=f"{true_score:.1f}%",
            annotation_position="bottom right"
        )

        if sondeur:
            polls = polls.filter(pl.col('Sondeur').is_in(sondeur))

        polls = polls.filter(pl.col('Échantillon')<=max_echantillon).filter(pl.col('Échantillon')>=min_echantillon).filter(pl.col('date')>=min_date).filter(pl.col('date')<=max_date)

        pdf = (
            polls
            .select(
                [
                    "date",
                    "Échantillon",
                    "Sondeur",
                    item,
                ]
            )
            .drop_nulls()
            .to_pandas()
            .sort_values("date")
        )


        if pdf.empty:
            continue


        pdf["date_num"] = (
            pd.to_datetime(
                pdf["date"]
            )
            .map(
                lambda x:
                x.timestamp()
            )
        )

        smooth = lowess(
            endog=pdf[item],
            exog=pdf["date_num"],
            frac=0.25,
        )

        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(
                    smooth[:,0],
                    unit="s",
                ),
                y=smooth[:,1],
                mode="lines",
                name=item,
                line=dict(
                    color=colors[item],
                    width=3,
                ),
                hoverinfo="skip",
            )
        )


        fig.add_trace(
            go.Scatter(
                x=pd.to_datetime(
                    pdf["date"]
                ),
                y=pdf[item],
                mode="markers",
                name=item,
                marker=dict(
                    color=colors[item],
                    size=(
                        pdf["Échantillon"]
                        /
                        350
                    )
                    .clip(
                        lower=5,
                        upper=20,
                    ),
                ),
                customdata=np.stack(
                    [
                        pdf["Sondeur"],
                        pdf["Échantillon"],
                    ],
                    axis=1,
                ),
                hovertemplate=(
                    "%{x|%d %b %Y}<br>"
                    "Sondeur: %{customdata[0]}"
                    "<br>"
                    "Échantillon: %{customdata[1]}"
                    "<extra></extra>"
                ),
            )
        )


    fig.update_layout(
        height=900,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=-0.2,
        ),
        yaxis_title="Intentions de vote (%)",
        xaxis_title="Date",
    )


    return fig


def _bloc_columns():

    from config import BLOCS

    return BLOCS