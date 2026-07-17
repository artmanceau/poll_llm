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
        results["VERSION"]
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
        r["N_RESPONDENTS"]
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
    # BAR PLOT
    # ==========================


    comparison = prepare_comparison_df(
        resume,
        official,
        year,
    )


    st.header(
        "Intentions de vote"
    )


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
            "bassin_de_vie",
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
            "bassin_de_vie",
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
                "Bassin de vie",
                sorted(
                    candidat_df["bassin_de_vie"]
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
                pl.col("bassin_de_vie") == geo
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
                f"{row['bassin_de_vie']})"
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

        normalize = st.checkbox(
            "Ramener aux suffrages exprimés "
            "(exclure abstention / vote blanc)",
            value=True,
        )

        with st.spinner(
            "Chargement de toutes les simulations…"
        ):

            all_summaries = load_all_summaries(year)

        if all_summaries.is_empty():

            st.warning(
                "Aucune simulation trouvée pour cette année."
            )

        else:

            bias = compute_bias(
                all_summaries,
                official,
                year,
                normalize=normalize,
            )

            st.plotly_chart(
                bias_scatter(bias),
                width="stretch",
            )
