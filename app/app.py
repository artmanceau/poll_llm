import streamlit as st
import polars as pl
import plotly.express as px

st.set_page_config(page_title="Explorateur du sondage LLM", layout="wide")

VERSION = "1783624824.0921388"
SUMMARY_PATH = "s3://arthurmanceau/poll_llm/results/summary_2027_1783624824.0921388.csv"
DETAIL_PATH = "s3://arthurmanceau/poll_llm/results/detailed_1783624824.0921388.csv"
YEAR = 2027
GEOJSON_PATH = "s3://arthurmanceau/poll_llm/geo/departements.geojson"

storage_options = {
    "profile": "default",
}

@st.cache_data
def charger_donnees():
    resume = pl.read_csv(
        SUMMARY_PATH,
        storage_options=storage_options
    )
    detail = pl.read_csv(
        DETAIL_PATH,
        storage_options=storage_options
    )
    return resume, detail


resume, detail = charger_donnees()

st.title("🗳️ Explorateur du sondage LLM")


# ============================================================
# SECTION 1 - VOTE GLOBAL
# ============================================================

st.header("Intentions de vote globales")

fig = px.bar(
    resume.to_pandas(),
    x=f"vote{YEAR}",
    y="pvote",
    text="pvote",
)

fig.update_traces(texttemplate="%{y:.1%}")

fig.update_layout(
    yaxis_title="Part des votes",
    xaxis_title="Candidat",
)

st.plotly_chart(
    fig,
    width='stretch'
)


# ============================================================
# SECTION 2 - SOCIO DEMOGRAPHIE
# ============================================================

with st.expander(
    "📊 Analyse socio-démographique",
    expanded=False
):

    variables = {
        "AGE": "Âge",
        "SEX": "Sexe",
        "PCS": "Catégorie socio-professionnelle",
        "GEO": "Département",
    }

    rows = [
        st.columns(2),
        st.columns(2)
    ]

    for idx, (variable, label) in enumerate(variables.items()):

        col = rows[idx // 2][idx % 2]

        with col:

            repartition = (
                detail
                .group_by(variable)
                .len()
                .sort("len", descending=True)
            )

            fig = px.bar(
                repartition.to_pandas(),
                x=variable,
                y="len",
                title=label,
            )

            fig.update_layout(
                height=350,
                margin=dict(
                    l=20,
                    r=20,
                    t=40,
                    b=20
                ),
                yaxis_title="Nombre de répondants",
                xaxis_title=label,
            )

            st.plotly_chart(
                fig,
                width='stretch'
            )


# ============================================================
# SECTION 3 - RAISONS DE VOTE
# ============================================================

with st.expander(
    "💬 Exploration des raisons de vote",
    expanded=False
):

    candidat = st.selectbox(
        "Candidat choisi",
        sorted(detail[f"vote{YEAR}"].unique().to_list()),
        key="candidate_reason"
    )

    candidat_df = detail.filter(
        pl.col(f"vote{YEAR}") == candidat
    )


    c1, c2, c3, c4 = st.columns(4)

    with c1:
        age = st.selectbox(
            "Âge",
            sorted(candidat_df["AGE"].unique().to_list()),
            index=None,
            key="filter_age"
        )

    with c2:
        pcs = st.selectbox(
            "Catégorie socio-professionnelle",
            sorted(candidat_df["PCS"].unique().to_list()),
            index=None,
            key="filter_pcs"
        )

    with c3:
        sexe = st.selectbox(
            "Sexe",
            sorted(candidat_df["SEX"].unique().to_list()),
            index=None,
            key="filter_sex"
        )

    with c4:
        geo = st.selectbox(
            "Département",
            sorted(candidat_df["GEO"].unique().to_list()),
            index=None,
            key="filter_geo"
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
            pl.col("GEO") == geo
        )


    st.write(
        f"**{resultats.height} répondants correspondants**"
    )


    st.subheader("Raisons exprimées")

    for row in resultats.iter_rows(named=True):

        texte = (
            f"{row['raison']} "
            f"— ({row['SEX']}, {row['AGE']}, "
            f"{row['PCS']}, {row['GEO']})"
        )

        st.info(texte)