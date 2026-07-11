import asyncio
from loguru import logger
import time
import polars as pl
from dotenv import load_dotenv
import s3fs
import posixpath

from config import MODEL, N_RESPONDENTS, WORKERS, PROMPT_FILE, YEAR, VERSION

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

RESULT_PATH = "s3://arthurmanceau/poll_llm/results/"
PROMPT_PATH = "s3://arthurmanceau/poll_llm/llm_prompts/"


def get_summary(df, year):
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
    
    # 1. Get representative sample

    quotas = get_quotas(N_RESPONDENTS)

    logger.success(
        f"Generated {quotas.height} quota profiles (data from 2023)",
    )
 
    # 2. Make LLMs vote

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

    # 3. Save and process results

    logger.info(
        f"Received {len(results)} model responses",
    )

    detailed = pl.DataFrame(
        results
    )

    summary = get_summary(
        detailed, YEAR
    )

    logger.success(YEAR)
    logger.success(summary)

    # Sample is stored
    detailed_path = posixpath.join(
        "s3://arthurmanceau",
        "poll_llm",
        "results",
        VERSION,
        MODEL,
        str(YEAR),
        str(N_RESPONDENTS),
        "detailed.csv",
    )
    detailed.write_csv(detailed_path)

    # Aggregated results
    summary_path = posixpath.join(
        "s3://arthurmanceau",
        "poll_llm",
        "results",
        VERSION,
        MODEL,
        str(YEAR),
        str(N_RESPONDENTS),
        "summary.csv",
    )
    summary.write_csv(summary_path)

    # Save prompt for audit
    fs = s3fs.S3FileSystem()
    prompt_path = posixpath.join(PROMPT_PATH, VERSION, "prompt_template.jinja2")
    with fs.open(prompt_path, "w", encoding="utf-8") as f:
        f.write(template.render())

    logger.info(f"Completed successfully in {time.time() - start:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())