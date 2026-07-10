import polars as pl
import numpy as np
from quotas.definitions import GENDER, AGE, CSP, DEPARTEMENT


def get_quotas(N=100):
    df = pl.scan_parquet(
        "s3://arthurmanceau/poll_llm/quota/quotas_data_insee.parquet",
    ).select(
        'GEO', 'GEO_OBJECT', 'AGE', 'SEX', 'PCS', 'OBS_VALUE',
    ).filter(
        (pl.col('PCS') != '_T') & (pl.col('AGE') != 'Y_GE15') & (pl.col('SEX') != '_T') & (pl.col('GEO_OBJECT') == 'DEP')
    ).collect()

    weights = df.get_column("OBS_VALUE").to_numpy()
    weights = weights / weights.sum()

    idx = np.random.choice(len(df), size=N, replace=True, p=weights)

    sample = df[idx.tolist()].with_columns(
        pl.col('AGE').cast(pl.String).replace(AGE),
        pl.col('PCS').cast(pl.String).replace(CSP),
        pl.col('GEO').cast(pl.String).replace(DEPARTEMENT),
        pl.col('SEX').cast(pl.String).replace(GENDER),
    ).select(
        'GEO', 'AGE', 'SEX', 'PCS'
    )
    sample.write_csv(
        "s3://arthurmanceau/poll_llm/quota/sample.csv"
    )
    return sample