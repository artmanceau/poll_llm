import asyncio
from loguru import logger
import time
import polars as pl
from dotenv import load_dotenv

from config import MODEL, N_RESPONDENTS, WORKERS, PROMPT_FILE, RESULT_FILE, RESULT_FILE_SUMMARY, YEAR

from quotas.get_quotas_data import (
    get_quotas,
)
from llm_utils.runner import (
    run
)
from prompts.prompts import (
    load_template
)
from prompts.candidates import (
    CANDIDATES
)


def summary(df, year):
    n = len(df)
    return (
        df
        .group_by(f"vote{year}")
        .agg(
            pl.len()
            .alias("vote"),
        )
        .sort(
            "vote",
            descending=True
        ).with_columns(
            pvote=(pl.col('vote') / n) * 100
        )
    )


async def main():

    start = time.time()
    ts = (start)

    load_dotenv()

    logger.info("Starting poll LLM simulation")
    logger.debug(
        f"Model={MODEL} respondents={N_RESPONDENTS} workers={WORKERS}",
    )
    logger.debug(
        f"Election présdientielle de {YEAR} (candidats: {CANDIDATES[YEAR]})",
    )
    logger.info(
        "Generating synthetic population based on quotas"
    )

    quotas = get_quotas(N_RESPONDENTS)

    logger.success(
        f"Generated {quotas.height} quota profiles (data from 2023)",
    )

    template = load_template(
        PROMPT_FILE
    )

    logger.debug(
        "Launching Ollama workers"
    )

    results = run(
        quotas,
        template,
        YEAR,
        MODEL,
        WORKERS
    )

    logger.info(
        f"Received {len(results)} model responses",
    )

    df = pl.DataFrame(
        results
    )

    result_summary_2027 = summary(
        df, 2027
    )

    print(2027)
    print(result_summary_2027)

    df.write_csv(
        RESULT_FILE + f'{YEAR}_{ts}.csv'
    )

    result_summary_2027.write_csv(
        RESULT_FILE_SUMMARY + f'{YEAR}_{ts}.csv'
    )

    logger.info(f"Completed successfully in {time.time() - start:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())