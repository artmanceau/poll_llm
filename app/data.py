import posixpath
import polars as pl
import s3fs
import streamlit as st

from config import (
    BUCKET_ROOT,
    CANDIDATES,
)

from dates import parse_poll_dates


storage_options = {
    "profile": "default",
}


fs = s3fs.S3FileSystem(
    profile="default",
    endpoint_url="https://minio.lab.sspcloud.fr",
    client_kwargs={
        "region_name": "us-east-1",
    },
)


@st.cache_data
def list_results():

    files = fs.glob(
        f"{BUCKET_ROOT}/*/*/*/*/*.csv"
    )

    rows = []

    for file in files:

        parts = file.replace(
            f"{BUCKET_ROOT}/",
            "",
        ).split("/")

        if len(parts) != 8:
            continue

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

    return (
        pl.DataFrame(rows)
        .unique()
    )


def build_paths(
    version,
    model,
    year,
    respondents,
):

    base = posixpath.join(
        BUCKET_ROOT,
        version,
        model,
        str(year),
        str(respondents),
    )

    return (
        posixpath.join(
            base,
            "summary.csv",
        ),
        posixpath.join(
            base,
            "detailed.csv",
        ),
    )


@st.cache_data
def load_llm_data(
    summary_path,
    detail_path,
):

    resume = pl.read_csv(
        summary_path,
        storage_options=storage_options,
    )

    detail = pl.read_csv(
        detail_path,
        storage_options=storage_options,
    )

    return resume, detail


@st.cache_data
def load_poll_data(
    year,
):

    columns = [
        "Sondeur",
        "Dates",
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
    ]


    rename = {
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
    }


    polls = (
        pl.read_parquet(
            f"s3://arthurmanceau/election_modeling_uhcp/data/polls/presidentiel/{year}/polls_t1.parquet",
            storage_options=storage_options,
        )
        .select(columns)
        .rename(rename)
    )


    official = (
        polls
        .filter(
            pl.col("Sondeur")
            ==
            "Résultats"
        )
        .select(CANDIDATES)
        .transpose(
            include_header=True
        )
        .rename(
            {
                "column": f"vote{year}",
                "column_0": "pvote",
            }
        )
        .with_columns(
            pl.lit(
                "Résultat officiel"
            )
            .alias("source"),

            pl.col("pvote")
            .cast(pl.Float64),
        )
    )


    polls = (
        polls
        .filter(
            pl.col("Sondeur")
            !=
            "Résultats"
        )
        .with_columns(
            pl.col(
                "Échantillon"
            )
            .cast(pl.Int64)
        )
    )


    polls = parse_poll_dates(
        polls,
        year,
    )


    return official, polls