import posixpath
import polars as pl
import s3fs
import streamlit as st

from config import (
    BUCKET_ROOT,
)
from utils import clean_env_var


candidates_2022 = [
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


def get_columns_poll_ds(candidates):
    return [f"C_{candidate}_processed" for candidate in candidates] + [
        "source",
        "date",
        "sample_size",
    ]


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
    "aws_access_key_id": st.secrets["AWS_ACCESS_KEY_ID"],
    "aws_secret_access_key": st.secrets["AWS_SECRET_ACCESS_KEY"],
    "aws_session_token": "",
    "aws_region": "us-east-1",
    "aws_endpoint_url": "https://minio.lab.sspcloud.fr",
}


fs = s3fs.S3FileSystem(
    endpoint_url="https://minio.lab.sspcloud.fr",
    key=st.secrets["AWS_ACCESS_KEY_ID"],
    secret=st.secrets["AWS_SECRET_ACCESS_KEY"],
)


@st.cache_data
def list_results():
    files = fs.glob(f"{BUCKET_ROOT}/*/*/*/*/*.csv")

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

    return pl.DataFrame(rows).unique()


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
    clean_env_var()

    resume = pl.scan_csv(
        summary_path,
        storage_options=storage_options,
    ).collect()

    detail = pl.scan_csv(
        detail_path,
        storage_options=storage_options,
    ).collect()

    return resume, detail


@st.cache_data
def load_all_summaries(year, min_version, min_n):
    """Load every version/model/respondents summary available for a year.

    Returns one row per (candidate, model combo) with identifying columns,
    so the bias tab can compare all LLM runs at once.
    """

    r = (
        list_results()
        .filter(pl.col("YEAR") == year)
        .filter(pl.col("VERSION") >= min_version)
        .filter(pl.col("N_RESPONDENTS") >= min_n)
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
            s = pl.scan_csv(
                summary_path,
                storage_options=storage_options,
            ).collect()

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
        .select(get_columns_poll_ds(candidates_2022))
        .rename(rename_dict)
        .filter(pl.col("source") == "Résultats")
        .select(list(rename_dict.values()))
        .transpose(include_header=True)
        .rename(
            {
                "column": f"vote{year}",
                "column_0": "pvote",
            }
        )
        .with_columns(
            pl.lit("Résultat officiel").alias("source"),
            pl.col("pvote").cast(pl.Float64),
        )
    )

    return polls
