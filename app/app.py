import streamlit as st
import polars as pl
from data import (
    list_results,
    build_paths,
    load_llm_data,
    load_official_results,
    load_all_summaries,
)

from utils import (
    prepare_comparison_df,
    compute_bias,
)

from plots import (
    global_bar_plot,
    bloc_bar_plot,
    aggregate_blocs,
    bias_scatter,
)


st.set_page_config(
    page_title="Explorateur du sondage LLM",
    layout="wide",
)

MIN_VERSION = "4"
MIN_N = 50

# ==========================
# CONFIGURATION
# ==========================

st.sidebar.header(
    "Configuration"
)


results = list_results()

if results.is_empty():

    st.error(
        "Aucun résultat trouvé"
    )

    st.stop()

version = st.sidebar.selectbox(
    "Version",
    sorted(
        results.filter(pl.col('VERSION') >= MIN_VERSION)["VERSION"]
        .unique()
        .to_list(),
        reverse=True,
    ),
)


r = results.filter(
    pl.col("VERSION")
    ==
    version
)


model = st.sidebar.selectbox(
    "Modèle",
    sorted(
        r["MODEL"]
        .unique()
        .to_list()
    ),
)


r = r.filter(
    pl.col("MODEL")
    ==
    model
)


year = st.sidebar.selectbox(
    "Année",
    sorted(
        r["YEAR"]
        .unique()
        .to_list(),
        reverse=True,
    ),
)


r = r.filter(
    pl.col("YEAR")
    ==
    year
)


respondents = st.sidebar.selectbox(
    "Répondants",
    sorted(
        r.filter(pl.col('N_RESPONDENTS')>MIN_N)["N_RESPONDENTS"]
        .unique()
        .to_list()
    ),
)



summary_path, detail_path = build_paths(
    version,
    model,
    year,
    respondents,
)

resume, detail = load_llm_data(
    summary_path,
    detail_path,
)

official = load_official_results(year)

st.title(
    "🗳️ Explorateur du sondage LLM"
)


# ==========================
# MODE
# ==========================

mode = st.sidebar.radio(
    "Niveau d'analyse",
    [
        "Candidats",
        "Blocs politiques",
    ],
)


tab_main, tab_bias = st.tabs(
    [
        "Sondage",
        "Biais des LLM",
    ]
)


# ==========================
# TAB — SONDAGE
# ==========================

with tab_main:

    st.info(
        f"""
        Modèle : {model}

        Année : {year}

        Répondants : {respondents}
        """
    )

    # ==========================
    # Participation
    # ==========================

    if 'probabilite' in detail.columns:
        st.header(
            "Taux de participation"
        )

        st.info("Le taux de participation est calculée comme la note moyenne sur une echelle de 0 à 100 que les répondants ont indiqué à propos de leur intention d\'aller voter")

        true_ppar = {
            2022: 0.8050,
            2017: 0.8361
        }
        if year in true_ppar:
            ppar = true_ppar[year]
            st.metric(value=ppar, label='Taux de participation réel',  delta_color='green', format='percent')
        else:
            ppar = None

        ppar_pred = detail.get_column('probabilite').mean()/10
        st.metric(value=ppar_pred, label='Taux de participation prédit par le sondage', format='percent', delta_color='blue', delta=ppar_pred-ppar)

    # ==========================
    # BAR PLOT
    # ==========================

    # Remove non-vote
    resume_wo_abstention = resume.filter(~(pl.col(f'vote{year}').is_in(['Abstention', 'Non inscrit', 'Vote blanc ou nul'])))
    n_vote = resume_wo_abstention.select('vote').sum().item()
    resume_wo_abstention = resume_wo_abstention.with_columns(
        pvote=(pl.col('vote') / n_vote) * 100
    )

    comparison = prepare_comparison_df(
        resume_wo_abstention,
        official,
        year,
    )

    st.header(
        "Intentions de vote"
    )

    st.info('Les intentions de vote sont déterminées en demandant aux répondants le candidat pour lequel ils comptent voter au premier tour')

    avg_error = resume_wo_abstention.join(
        official, on=f'vote{year}'
    ).rename(
        {'pvote_right': 'off', 'pvote': 'pred'}
    ).with_columns(
        avg_error=(pl.col('off') - pl.col('pred')).abs() / 100
    ).select('avg_error').mean().item()

    st.metric(value=avg_error, label='Erreur absolue moyenne', format='percent')


    if mode == "Candidats":

        fig = global_bar_plot(
            comparison,
            year,
        )

    else:

        bloc_df = aggregate_blocs(
            comparison,
            year,
        )

        fig = bloc_bar_plot(
            bloc_df
        )


    st.plotly_chart(
        fig,
        width="stretch",
    )


    # ==========================
    # SOCIO DEMO
    # ==========================


    with st.expander(
        "📊 Analyse socio-démographique"
    ):

        rows = [
            st.columns(2),
            st.columns(2),
        ]

        variables = [
            "AGE",
            "SEX",
            "PCS",
            "dep",
        ]

        for i, col_name in enumerate(variables):
            row = i // 2
            col = i % 2

            with rows[row][col]:

                st.subheader(col_name)

                chart_df = (
                    detail
                    .group_by(col_name)
                    .len()
                    .sort(
                        "len",
                        descending=True,
                    )
                    .to_pandas()
                    .set_index(col_name)
                )

                st.bar_chart(
                    chart_df,
                    height=350,
                )


    # ==========================
    # RAISONS
    # ==========================


    with st.expander(
        "💬 Raisons de vote"
    ):


        candidat = st.selectbox(
            "Candidat choisi",
            sorted(
                detail[f"vote{year}"]
                .unique()
                .to_list()
            ),
            key="candidate_reason",
        )


        candidat_df = detail.filter(
            pl.col(f"vote{year}") == candidat
        )

        rows = [
            st.columns(2),
            st.columns(2),
        ]

        variables = [
            "AGE",
            "SEX",
            "PCS",
            "dep",
        ]

        for i, col_name in enumerate(variables):
            row = i // 2
            col = i % 2

            with rows[row][col]:

                st.subheader(col_name)

                chart_df = (
                    candidat_df
                    .group_by(col_name)
                    .len()
                    .sort(
                        "len",
                        descending=True,
                    )
                    .to_pandas()
                    .set_index(col_name)
                )

                st.bar_chart(
                    chart_df,
                    height=350,
                )


        c1, c2, c3, c4 = st.columns(4)


        with c1:
            age = st.selectbox(
                "Âge",
                sorted(
                    candidat_df["AGE"]
                    .unique()
                    .to_list()
                ),
                index=None,
                key="filter_age",
            )


        with c2:
            pcs = st.selectbox(
                "Catégorie socio-professionnelle",
                sorted(
                    candidat_df["PCS"]
                    .unique()
                    .to_list()
                ),
                index=None,
                key="filter_pcs",
            )


        with c3:
            sexe = st.selectbox(
                "Sexe",
                sorted(
                    candidat_df["SEX"]
                    .unique()
                    .to_list()
                ),
                index=None,
                key="filter_sex",
            )


        with c4:
            geo = st.selectbox(
                "dep",
                sorted(
                    candidat_df["dep"]
                    .unique()
                    .to_list()
                ),
                index=None,
                key="filter_geo",
            )


        resultats = candidat_df


        if age is not None:
            resultats = resultats.filter(
                pl.col("AGE") == age
            )


        if pcs is not None:
            resultats = resultats.filter(
                pl.col("PCS") == pcs
            )


        if sexe is not None:
            resultats = resultats.filter(
                pl.col("SEX") == sexe
            )


        if geo is not None:
            resultats = resultats.filter(
                pl.col("dep") == geo
            )


        st.write(
            f"**{resultats.height} répondants correspondants**"
        )


        st.subheader(
            "Raisons exprimées"
        )


        for row in resultats.iter_rows(
            named=True
        ):

            texte = (
                f"{row['raison']} "
                f"— ({row['SEX']}, "
                f"{row['AGE']}, "
                f"{row['PCS']}, "
                f"{row['commune']} — "
                f"{row['dep']})"
            )

            st.info(texte)


# ==========================
# TAB — BIAIS DES LLM
# ==========================

with tab_bias:

    st.header(
        f"Biais des LLM — présidentielle {year}"
    )

    st.caption(
        "Chaque point est une simulation (modèle × version × répondants). "
        "L'axe horizontal mesure le biais en faveur de la droite et l'axe"
        "vertical l'erreur moyenne sur tous les candidats"
    )

    if official.is_empty():

        st.warning(
            f"Aucun résultat officiel disponible pour {year} : "
            "le biais ne peut pas être calculé."
        )

    else:
        with st.spinner(
            "Chargement de toutes les simulations…"
        ):

            all_summaries = load_all_summaries(year, MIN_VERSION, MIN_N)

        if all_summaries.is_empty():

            st.warning(
                "Aucune simulation trouvée pour cette année."
            )

        else:

            bias = compute_bias(
                all_summaries,
                official,
                year,
            )

            st.plotly_chart(
                bias_scatter(bias),
                width="stretch",
            )
