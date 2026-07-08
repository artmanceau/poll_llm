import polars as pl
import itertools


sexe = {
    "Homme": 0.49,
    "Femme": 0.51
}

age = {
    "18-24": 0.12,
    "25-34": 0.16,
    "35-49": 0.23,
    "50-64": 0.25,
    "65+": 0.24
}

csp = {
    "Cadre": 0.18,
    "Employe": 0.32,
    "Ouvrier": 0.20,
    "Retraite": 0.30
}

departement = {
    "75": 0.08,
    "13": 0.06,
    "33": 0.04,
    "59": 0.05,
    "69": 0.05,
    "autres": 0.72
}


rows = []

for s, a, c, d in itertools.product(
    sexe,
    age,
    csp,
    departement
):
    rows.append(
        {
            "sexe": s,
            "age": a,
            "csp": c,
            "departement": d,
            "weight": (
                sexe[s]
                * age[a]
                * csp[c]
                * departement[d]
            )
        }
    )


quotas = pl.DataFrame(rows)

quotas = quotas.with_columns(
    (
        pl.col("weight")
        / pl.col("weight").sum()
    )
    .alias("weight")
)


quotas.write_csv(
    "quotas/quotas.csv"
)

print(quotas)
print(
    quotas["weight"].sum()
)