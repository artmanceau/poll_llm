import posixpath
import polars as pl
import s3fs
import streamlit as st

from config import (
    BUCKET_ROOT,
)

candidates = [
        "arthaud",
        "poutou",
        "roussel",
        "melenchon",
        "hidalgo",
        "jadot",
        "macron",
        "pecresse",
        "lassalle",
        "dupont_aignan",
        "m_le_pen",
        "zemmour",
]
columns = [f'C_{candidate}_processed' for candidate in candidates] + ["source", "date", "sample_size"]

rename_dict = {
        "C_arthaud_processed": "Nathalie Arthaud (Lutte ouvrière)",
        "C_poutou_processed": "Philippe Poutou (Nouveau Parti anticapitaliste)",
        "C_roussel_processed": "Fabien Roussel (Parti communiste français)",
        "C_melenchon_processed": "Jean-Luc Mélenchon (La France insoumise)",
        "C_hidalgo_processed": "Anne Hidalgo (Parti Socialiste)",
        "C_jadot_processed": "Yannick Jadot (Europe Écologie Les Verts)",
        "C_macron_processed": "Emmanuel Macron (La République en marche)",
        "C_pecresse_processed": "Valérie Pécresse (Les Républicains)",
        "C_lassalle_processed": "Jean Lassalle (Résistons)",
        "C_dupont_aignan_processed": "Nicolas Dupont-Aignan (Debout la France)",
        "C_m_le_pen_processed": "Marine Le Pen (Rassemblement national)",
        "C_zemmour_processed": "Éric Zemmour (Reconquête)",
}

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
    
    polls = (
        pl.read_parquet(
            f"s3://arthurmanceau/poll_tracker/wiki/presidentiel/{year}/t1/polls.parquet",
            storage_options=storage_options,
        )
        .select(columns)
        .rename(rename_dict)
        .filter(
            pl.col("source")
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
