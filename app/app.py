import streamlit as st
import polars as pl
import plotly.express as px
import s3fs
import posixpath
from statsmodels.nonparametric.smoothers_lowess import lowess
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from plotly import graph_objects as go
from parser_date import parse_poll_date
import colorsys

load_dotenv()


st.set_page_config(
    page_title="Explorateur du sondage LLM",
    layout="wide",
)

BUCKET_ROOT = "s3://arthurmanceau/poll_llm/results"


fs = s3fs.S3FileSystem(
    profile="default",
    endpoint_url="https://minio.lab.sspcloud.fr",
    client_kwargs={"region_name": "us-east-1"},
)
storage_options = {
    'profile': 'default'
}
BLOCS = {
    "G": [
        "Nathalie Arthaud (Lutte ouvrière)",
        "Philippe Poutou (Nouveau Parti anticapitaliste)",
        "Fabien Roussel (Parti communiste français)",
        "Jean-Luc Mélenchon (La France insoumise)",
    ],
    "CG": [
        "Anne Hidalgo (Parti Socialiste)",
        "Yannick Jadot (Europe Écologie Les Verts)",
    ],
    "C": [
        "Emmanuel Macron (La République en marche)",
        'Jean Lassalle (Résistons)'
    ],
    "CD": [
        "Valérie Pécresse (Les Républicains)",
    ],
    "D": [
        "Nicolas Dupont-Aignan (Debout la France)",
        "Marine Le Pen (Rassemblement national)",
        "Éric Zemmour (Reconquête)",
    ],
}

candidates = [
    "Nathalie Arthaud (Lutte ouvrière)",
    "Philippe Poutou (Nouveau Parti anticapitaliste)",
    "Fabien Roussel (Parti communiste français)",
    "Jean-Luc Mélenchon (La France insoumise)",
    "Anne Hidalgo (Parti Socialiste)",
    "Yannick Jadot (Europe Écologie Les Verts)",
    "Emmanuel Macron (La République en marche)",
    "Valérie Pécresse (Les Républicains)",
    "Jean Lassalle (Résistons)",
    "Nicolas Dupont-Aignan (Debout la France)",
    "Marine Le Pen (Rassemblement national)",
    "Éric Zemmour (Reconquête)",
]


CANDIDATE_COLORS = {
    "Nathalie Arthaud (Lutte ouvrière)": "#B22222",              # dark red
    "Philippe Poutou (Nouveau Parti anticapitaliste)": "#E53935", # bright red
    "Fabien Roussel (Parti communiste français)": "#C00000",     # PCF red
    "Jean-Luc Mélenchon (La France insoumise)": "#C62828",       # LFI red
    "Anne Hidalgo (Parti Socialiste)": "#E91E63",                # PS pink
    "Yannick Jadot (Europe Écologie Les Verts)": "#4CAF50",      # green
    "Emmanuel Macron (La République en marche)": "#F4C542",      # gold/yellow
    "Valérie Pécresse (Les Républicains)": "#0055A4",            # LR blue
    "Jean Lassalle (Résistons)": "#4E342E",                      # brown
    "Nicolas Dupont-Aignan (Debout la France)": "#1E88E5",       # sovereignist blue
    "Marine Le Pen (Rassemblement national)": "#0B3D91",         # RN navy
    "Éric Zemmour (Reconquête)": "#5C0011",                      # burgundy
}

candidate_to_bloc = {
    candidate: bloc
    for bloc, candidates_bloc in BLOCS.items()
    for candidate in candidates_bloc
}

smooth_result = pl.DataFrame(
    {
        f"vote2022": candidates,
        "pvote": [
            0.5555522914642451,
            0.999999999999226,
            2.6915058730916215,
            17.16201220054569,
            2.0511403432017308,
            4.906673937286057,
            26.22890349406319,
            8.371935740613074,
            2.709478368598444,
            2.3018239511475214,
            23.1476141442254,
            8.886892008663699,
        ],
        "source": ["sondages"] * len(candidates),
    }
)

@st.cache_data
def list_results():
    files = fs.glob(f"{BUCKET_ROOT}/*/*/*/*/*.csv")

    rows = []

    for f in files:
        parts = f.replace(f"{BUCKET_ROOT}/", "").split("/")

        if len(parts) == 8:
            _, _, _, version, model, year, n_respondents, filename = parts

            rows.append(
                {
                    "VERSION": version,
                    "MODEL": model,
                    "YEAR": int(year),
                    "N_RESPONDENTS": int(n_respondents),
                    "FILE": filename,
                }
            )

    return pl.DataFrame(rows).unique()


results = list_results()

if results.is_empty():
    st.error("Aucun résultat trouvé dans S3")
    st.stop()


st.sidebar.header("Configuration")


VERSION = st.sidebar.selectbox(
    "Version",
    sorted(
        results["VERSION"].unique().to_list(),
        reverse=True,
    ),
)


filtered = results.filter(
    pl.col("VERSION") == VERSION
)


MODEL = st.sidebar.selectbox(
    "Modèle",
    sorted(
        filtered["MODEL"].unique().to_list()
    ),
)


filtered = filtered.filter(
    pl.col("MODEL") == MODEL
)


YEAR = st.sidebar.selectbox(
    "Année",
    sorted(
        filtered["YEAR"].unique().to_list(),
        reverse=True,
    ),
)


filtered = filtered.filter(
    pl.col("YEAR") == YEAR
)


N_RESPONDENTS = st.sidebar.selectbox(
    "Nombre de répondants",
    sorted(
        filtered["N_RESPONDENTS"].unique().to_list()
    ),
)


SUMMARY_PATH = posixpath.join(
    BUCKET_ROOT,
    VERSION,
    MODEL,
    str(YEAR),
    str(N_RESPONDENTS),
    "summary.csv",
)


DETAIL_PATH = posixpath.join(
    BUCKET_ROOT,
    VERSION,
    MODEL,
    str(YEAR),
    str(N_RESPONDENTS),
    "detailed.csv",
)


@st.cache_data
def load_data(summary_path, detail_path):
    resume = pl.read_csv(
        summary_path,
        storage_options=storage_options,
    )

    detail = pl.read_csv(
        detail_path,
        storage_options=storage_options,
    )

    return resume, detail


resume, detail = load_data(
    SUMMARY_PATH,
    DETAIL_PATH,
)


@st.cache_data
def load_poll_data(YEAR):
    poll_data = pl.read_parquet(
        f's3://arthurmanceau/election_modeling_uhcp/data/polls/presidentiel/{YEAR}/polls_t1.parquet',
        storage_options=storage_options).select([
        'Sondeur',
        'Dates',
        "Échantillon",
        "Arthaud (LO)",
        "Poutou (NPA)",
        "Roussel (PCF)",
        "Mélenchon (LFI)",
        "Hidalgo (PS)",
        "Jadot (EÉLV)",
        "Macron (LREM)",
        "Pécresse (LR)",
        "Lassalle (RES)",
        "Dupont-Aignan (DLF)",
        "Le Pen (RN)",
        "Zemmour (REC)",
    ]).rename({
        "Arthaud (LO)": "Nathalie Arthaud (Lutte ouvrière)",
        "Poutou (NPA)": "Philippe Poutou (Nouveau Parti anticapitaliste)",
        "Roussel (PCF)": "Fabien Roussel (Parti communiste français)",
        "Mélenchon (LFI)": "Jean-Luc Mélenchon (La France insoumise)",
        "Hidalgo (PS)": "Anne Hidalgo (Parti Socialiste)",
        "Jadot (EÉLV)": "Yannick Jadot (Europe Écologie Les Verts)",
        "Macron (LREM)": "Emmanuel Macron (La République en marche)",
        "Pécresse (LR)": "Valérie Pécresse (Les Républicains)",
        "Lassalle (RES)": "Jean Lassalle (Résistons)",
        "Dupont-Aignan (DLF)": "Nicolas Dupont-Aignan (Debout la France)",
        "Le Pen (RN)": "Marine Le Pen (Rassemblement national)",
        "Zemmour (REC)": "Éric Zemmour (Reconquête)",
    })
    resultat = poll_data.filter(pl.col('Sondeur')=='Résultats').select( "Nathalie Arthaud (Lutte ouvrière)", "Philippe Poutou (Nouveau Parti anticapitaliste)", "Fabien Roussel (Parti communiste français)", "Jean-Luc Mélenchon (La France insoumise)", "Anne Hidalgo (Parti Socialiste)", "Yannick Jadot (Europe Écologie Les Verts)", "Emmanuel Macron (La République en marche)", "Valérie Pécresse (Les Républicains)", "Jean Lassalle (Résistons)", "Nicolas Dupont-Aignan (Debout la France)", "Marine Le Pen (Rassemblement national)", "Éric Zemmour (Reconquête)").transpose(include_header=True).rename({
        "column": f"vote{YEAR}",
        "column_0": "pvote",
    }).with_columns(
        pl.lit("Résultat officiel").alias("source"),
        pl.col('pvote').cast(pl.Float64)
    )
    sondages = poll_data.filter(pl.col('Sondeur')!='Résultats').with_columns(
        pl.col("Échantillon").cast(pl.Int64),
    )

    MONTHS = {
        "janvier": 1,
        "février": 2,
        "mars": 3,
        "avril": 4,
        "mai": 5,
        "juin": 6,
        "juillet": 7,
        "août": 8,
        "septembre": 9,
        "octobre": 10,
        "novembre": 11,
        "décembre": 12,
    }

    sondages = sondages.with_columns(
        pl.col("Dates")
        .str.to_lowercase()
        .str.replace_all("\u00a0", " ")
        .str.replace_all("1er", "1")
        .alias("date_clean")
    )

    sondages = sondages.with_columns(
        pl.col("date_clean")
        .str.extract(r"(\d+)\s*([a-zéû]+)\s*$", 1)
        .cast(pl.Int32)
        .alias("day"),

        pl.col("date_clean")
        .str.extract(r"(\d+)\s*([a-zéû]+)\s*$", 2)
        .alias("month_name"),
    )

    sondages = sondages.with_columns(
        pl.col("month_name")
        .replace(MONTHS)
        .cast(pl.Int32)
        .alias("month")
    )

    sondages = sondages.with_columns(
        pl.datetime(
            YEAR,
            pl.col("month"),
            pl.col("day"),
        ).alias("date")
    )

    sondages = sondages.with_columns(
        (
            pl.col("month") > pl.col("month").shift(1)
        )
        .fill_null(False)
        .cast(pl.Int32)
        .cum_sum()
        .alias("year_offset")
    )

    sondages = sondages.with_columns(
        pl.col("date")
        .dt.offset_by(
            (-pl.col("year_offset"))
            .cast(pl.String)
            + "y"
        )
        .alias("date")
    )
    return resultat, sondages.filter(pl.col('date')>pl.date(2022, 1, 1))


resultat, sondages = load_poll_data(YEAR)

st.title("🗳️ Explorateur du sondage LLM")

st.warning(
    f"Modèle utilisé: {MODEL} | "
    f"Année: {YEAR} | "
    f"Répondants: {N_RESPONDENTS}"
)


# ============================================================
# SECTION 1 - VOTE GLOBAL
# ============================================================

st.header("Intentions de vote globales")

def adjust_color(hex_color, factor):
    hex_color = hex_color.lstrip("#")
    r, g, b = (
        int(hex_color[i:i+2], 16) / 255
        for i in (0, 2, 4)
    )
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0, min(1, l * factor))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02x}{:02x}{:02x}".format(
        int(r * 255),
        int(g * 255),
        int(b * 255),
    )


CANDIDATE_BAR_COLORS = {}

for candidate, color in CANDIDATE_COLORS.items():
    CANDIDATE_BAR_COLORS[(candidate, "LLM poll")] = adjust_color(color, 1.0)
    CANDIDATE_BAR_COLORS[(candidate, "Résultat réel")] = adjust_color(color, 1.0)
    CANDIDATE_BAR_COLORS[(candidate, "Sondages tendance")] = adjust_color(color, 1.0)

SOURCE_PATTERNS = {
    "LLM poll": ".",
    "Résultat réel": "",
    "Sondages tendance": "/",
}

plot_df = pl.concat(
    [
        resume.select(
            f"vote{YEAR}",
            "pvote"
        ).with_columns(
            pl.lit("LLM poll").alias("source")
        ),
        resultat.with_columns(
            pl.lit("Résultat réel").alias("source")
        ),
        smooth_result.with_columns(
            pl.lit("Sondages tendance").alias("source")
        ),
    ]
)

fig = go.Figure()

for source in plot_df["source"].unique():

    df_source = plot_df.filter(pl.col('source')==source).to_pandas()

    fig.add_trace(
        go.Bar(
            x=df_source[f"vote{YEAR}"],
            y=df_source["pvote"],
            name=source,
            text=df_source["pvote"],
            texttemplate="%{y:.1f}%",
            textposition="outside",
            marker=dict(
                color=[
                    CANDIDATE_BAR_COLORS[
                        (candidate, source)
                    ]
                    for candidate in df_source[f"vote{YEAR}"]
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
    xaxis_title="Candidat",
    yaxis_title="Intentions de vote (%)",
    legend_title="Source",
)

st.plotly_chart(
    fig,
    width="stretch",
)

# ============================================================
# SECTION 1 - VOTE BLOC
# ============================================================

plot_blocs = (
    plot_df
    .with_columns(
        pl.col(f"vote{YEAR}")
        .replace(candidate_to_bloc)
        .alias("bloc")
    )
    .group_by(
        "bloc",
        "source",
    )
    .agg(
        pl.col("pvote").sum()
    )
)

fig = go.Figure()

BLOC_COLORS = {
    "G": "#B22222",
    "CG": "#E91E63",
    "C": "#F4C542",
    "CD": "#0055A4",
    "D": "#0B3D91",
}

for source in plot_blocs["source"].unique():

    df_source = (
        plot_blocs
        .filter(pl.col("source") == source)
        .to_pandas()
    )
   

    fig.add_trace(
        go.Bar(
            x=df_source["bloc"],
            y=df_source["pvote"],
            name=source,
            text=df_source["pvote"],
            texttemplate="%{y:.1f}%",
            textposition="outside",
            marker=dict(
                color=[
                    BLOC_COLORS[b]
                    for b in df_source["bloc"]
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
    xaxis_title="Bloc politique",
    yaxis_title="Intentions de vote (%)",
    legend_title="Source",
)

st.plotly_chart(
    fig,
    width="stretch",
)

# ============================================================
# SECTION 2 - SONDAGES
# ============================================================

st.header("Sondages pour l'election")

df = sondages.select(
    ["date", "Échantillon", 'Sondeur'] + candidates
).to_pandas()

df = df.sort_values("date")

fig = go.Figure()

for candidate in candidates:
    true_score = (
        resultat
        .filter(pl.col(f"vote{YEAR}") == candidate)
        .select("pvote")
        .item()
    )

    fig.add_hline(
        y=true_score,
        line_width=2,
        line_color=CANDIDATE_COLORS[candidate],
        annotation_text=f"{true_score:.1f}%",
        annotation_position="right",
    )
    pdf = df[["date", "Échantillon", candidate]].dropna().copy()
    pdf = pdf.sort_values("date")

    pdf["date_num"] = pdf["date"].map(lambda x: x.timestamp())

    smooth = lowess(
        pdf[candidate],
        pdf["date_num"],
        frac=0.25,
    )

    smooth_dates = pd.to_datetime(smooth[:, 0], unit="s")

    fig.add_trace(
        go.Scatter(
            x=smooth_dates,
            y=smooth[:, 1],
            mode="lines",
            name=f"{candidate} (tendance)",
            line=dict(
                color=CANDIDATE_COLORS[candidate],
                width=3,
            ),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=pd.to_datetime(df["date"]),
            y=df[candidate],
            mode="markers",
            name=candidate,
            marker=dict(
                color=CANDIDATE_COLORS[candidate],
                size=(df["Échantillon"] / 350).clip(lower=5, upper=20),
            ),
            customdata=np.stack(
                [
                    df["Sondeur"],
                    df["Échantillon"],
                ],
                axis=-1,
            ),
            hovertemplate=(
                "%{x|%d %b %Y}<br>"
                f"<b>{candidate}</b>: "+"%{y:.1f}%<br>"
                "Sondeur: %{customdata[0]}<br>"
                "Échantillon: %{customdata[1]:,}<extra></extra>"
            ),
        )
    )

fig.update_layout(
    height=1200,
    width=2000,
    margin=dict(
        l=80,
        r=80,
        t=80,
        b=100,
    )
)

fig.update_layout(
    legend=dict(
        title="Candidat",
        orientation="h",
        yanchor="top",
        y=-0.15,
        xanchor="center",
        x=0.5,
        itemclick="toggle",
        itemdoubleclick="toggleothers",
    ),
    margin=dict(
        b=150,
    ),
)


fig.update_layout(
    yaxis=dict(
        title="Intentions de vote (%)",
        type="linear",
    )
)

st.plotly_chart(
    fig,
    width='stretch',
)

# ============================================================
# SECTION 2 - SOCIO DEMOGRAPHIE
# ============================================================


st.divider()

with st.expander(
    "📊 Analyse socio-démographique",
    expanded=False,
):

    variables = {
        "AGE": "Âge",
        "SEX": "Sexe",
        "PCS": "Catégorie socio-professionnelle",
        "bassin_de_vie": "Bassin de vie",
    }


    rows = [
        st.columns(2),
        st.columns(2),
    ]


    for idx, (variable, label) in enumerate(variables.items()):

        col = rows[idx // 2][idx % 2]


        with col:

            repartition = (
                detail
                .group_by(variable)
                .len()
                .sort(
                    "len",
                    descending=True,
                )
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
                    b=20,
                ),
                yaxis_title="Nombre de répondants",
                xaxis_title=label,
            )


            st.plotly_chart(
                fig,
                width="stretch",
            )


# ============================================================
# SECTION 3 - RAISONS DE VOTE
# ============================================================

with st.expander(
    "💬 Exploration des raisons de vote",
    expanded=False,
):


    candidat = st.selectbox(
        "Candidat choisi",
        sorted(
            detail[f"vote{YEAR}"]
            .unique()
            .to_list()
        ),
        key="candidate_reason",
    )


    candidat_df = detail.filter(
        pl.col(f"vote{YEAR}") == candidat
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