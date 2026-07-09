import polars as pl
import numpy as np

df = pl.scan_parquet(
    "s3://arthurmanceau/poll_llm/quota/quotas_data_insee.parquet",
    storage_options={
            "aws_endpoint_url": "https://minio.lab.sspcloud.fr",
            "aws_region": "us-east-1",
        },
        credential_provider=pl.CredentialProviderAWS(
            profile_name="default",
            region_name="us-east-1",
        )
).select(
    'GEO', 'GEO_OBJECT', 'AGE', 'SEX', 'PCS', 'OBS_VALUE',
).filter(
    (pl.col('PCS') != '_T') & (pl.col('AGE')!= 'Y_GE15') & (pl.col('SEX') != '_T') & (pl.col('GEO_OBJECT') == 'DEP')
)
total = df.select('OBS_VALUE').sum().collect().item()
df = df.with_columns(
    total = pl.lit(total)
).with_columns(
    share = pl.col('OBS_VALUE') / pl.col('total')
).collect()

N = 1000
weights = df["share"].to_numpy()
weights = weights / weights.sum()
idx = np.random.choice(
    len(df),
    size=N,
    replace=True,
    p=weights
)
sample = df[idx.tolist()]

print(sample.select('GEO', 'AGE', 'SEX', 'PCS'))

sample.select('GEO', 'AGE', 'SEX', 'PCS').write_csv('quotas/sample.csv')