import posixpath
import polars as pl
import s3fs
import streamlit as st

from config import (
    BUCKET_ROOT,
)


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
def load_all_summaries(
    year,
):
    """Load every version/model/respondents summary available for a year.

    Returns one row per (candidate, model combo) with identifying columns,
    so the bias tab can compare all LLM runs at once.
    """

    r = list_results().filter(
        pl.col("YEAR") == year
    )

    frames = []

    for row in r.iter_rows(named=True):

        summary_path, _ = build_paths(
            row["VERSION"],
            row["MODEL"],
            year,
            row["N_RESPONDENTS"],
        )

        try:
            s = pl.read_csv(
                summary_path,
                storage_options=storage_options,
            )
        except Exception:
            continue

        frames.append(
            s.select(
                [
                    f"vote{year}",
                    "pvote",
                ]
            ).with_columns(
                pl.lit(row["VERSION"]).alias("version"),
                pl.lit(row["MODEL"]).alias("model"),
                pl.lit(row["N_RESPONDENTS"]).alias("respondents"),
            )
        )

    if not frames:
        return pl.DataFrame()

    return pl.concat(frames)


@st.cache_data
def load_official_results(
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


    rename_dict = {
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
        .rename(rename_dict)
        .filter(
            pl.col("Sondeur")
            ==
            "Résultats"
        ).select(
            list(rename_dict.values())
        ).transpose(
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

    return polls
