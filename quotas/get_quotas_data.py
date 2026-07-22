import polars as pl
import numpy as np
from quotas.definitions import GENDER, AGE, CSP, DEPARTEMENT

# Source
# https://catalogue-donnees.insee.fr/fr/catalogue/recherche/DS_RP_TD_POPULATION_PCSAGESEX_COMP 


def get_quotas(N=100):
    codes = pl.scan_csv(
        "s3://arthurmanceau/poll_llm/quota/geo_codes.csv",
        storage_options={
            "aws_endpoint_url": "https://minio.lab.sspcloud.fr",
            "aws_region": "us-east-1",
        },
        credential_provider=pl.CredentialProviderAWS(
            profile_name="default",
            region_name="us-east-1",
        ),
        truncate_ragged_lines=True,
        separator=";",
    ).select(
        'libelle français', 'code'
    ).with_columns(
       pl.col("code").str.split_exact("-", 1).alias("code_parts")
    ).unnest(
        "code_parts"
    ).rename({
        "field_0": "GEO_OBJECT",
        "field_1": "GEO",
        'libelle français': 'name'}
    )

    codes_communes = codes.rename({
        'name': 'commune'}
    ).filter(
        pl.col('GEO_OBJECT') == 'COM'
    ).select(
        'GEO', 'commune'
    )
    codes_dep = codes.rename({
        'name': 'dep'}
    ).filter(
        pl.col('GEO_OBJECT') == 'DEP'
    ).select(
        'GEO', 'dep'
    )

    df = pl.scan_parquet(
        "s3://arthurmanceau/poll_llm/quota/quotas_data_insee.parquet",
        storage_options={
            "aws_endpoint_url": "https://minio.lab.sspcloud.fr",
            "aws_region": "us-east-1",
        },
        credential_provider=pl.CredentialProviderAWS(
            profile_name="default",
            region_name="us-east-1",
        ),
    ).select(
        'GEO', 'GEO_OBJECT', 'AGE', 'SEX', 'PCS', 'OBS_VALUE',
    ).filter(
        (pl.col('PCS') != '_T') & (pl.col('AGE') != 'Y_GE15') & (pl.col('SEX') != '_T') & (pl.col('GEO_OBJECT') == 'COM')
    ).with_columns(
        pl.col('GEO').cast(pl.String)
    ).join(
        codes_communes, on='GEO'
    ).collect()

    weights = df.get_column("OBS_VALUE").to_numpy()
    weights = weights / weights.sum()

    idx = np.random.choice(len(df), size=N, replace=True, p=weights)

    sample = df[idx.tolist()].with_columns(
        pl.col('AGE').cast(pl.String).replace(AGE),
        pl.col('PCS').cast(pl.String).replace(CSP),
        pl.col('SEX').cast(pl.String).replace(GENDER),
    ).with_columns(
        dep_=pl.when(pl.col('GEO').str.starts_with('97'))
        .then(pl.col('GEO').str.slice(0, 3))
        .otherwise(pl.col("GEO").str.slice(0, 2))
    ).with_columns(
        pl.col('dep_').cast(pl.String).replace(DEPARTEMENT).alias('dep')
    ).select(
        'commune', 'AGE', 'SEX', 'PCS', 'dep'
    )
    return sample
