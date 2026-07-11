import streamlit as st
import polars as pl

from config import (
    CANDIDATES,
)

from data import (
    list_results,
    build_paths,
    load_llm_data,
    load_poll_data,
)

from utils import (
    prepare_comparison_df,
)

from plots import (
    global_bar_plot,
    bloc_bar_plot,
    aggregate_blocs,
    poll_evolution_plot,
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


official, polls = load_poll_data(
    year
)



st.title(
    "🗳️ Explorateur du sondage LLM"
)


st.info(
    f"""
    Modèle : {model}

    Année : {year}

    Répondants : {respondents}
    """
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



# ==========================
# BAR PLOT
# ==========================


comparison = prepare_comparison_df(
    resume,
    official,
    official.rename(
        {
            "source":
            "old"
        }
    ),
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
# EVOLUTION SONDAGES
# ==========================


st.header(
    "Evolution des sondages"
)


if mode == "Candidats":

    fig = poll_evolution_plot(
        polls,
        official,
        year,
        mode="candidate",
    )

else:

    fig = poll_evolution_plot(
        polls,
        official,
        year,
        mode="bloc",
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


    for col in [
        "AGE",
        "SEX",
        "PCS",
        "bassin_de_vie",
    ]:

        st.subheader(col)

        st.bar_chart(
            detail
            .group_by(col)
            .len()
            .sort(
                "len",
                descending=True,
            )
            .to_pandas()
            .set_index(col)
        )



# ==========================
# RAISONS
# ==========================


with st.expander(
    "💬 Raisons de vote"
):


    candidate = st.selectbox(
        "Candidat",
        CANDIDATES,
    )


    reasons = (
        detail
        .filter(
            pl.col(
                f"vote{year}"
            )
            ==
            candidate
        )
    )


    st.write(
        f"{reasons.height} réponses"
    )


    for row in reasons.iter_rows(
        named=True
    ):

        st.info(
            row["raison"]
        )