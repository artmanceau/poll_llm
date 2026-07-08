import polars as pl
import numpy as np


def load_quotas(path):

    return (
        pl.read_csv(path)
        .with_columns(
            (
                pl.col("weight")
                / pl.col("weight").sum()
            )
            .alias("probability")
        )
    )


def generate_population(
    quotas,
    n
):

    idx = np.random.choice(
        quotas.height,
        size=n,
        replace=True,
        p=quotas["probability"].to_numpy()
    )

    return (
        quotas
        .gather(idx.tolist())
        .to_dicts()
    )