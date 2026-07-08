import asyncio
import logging
import time
import polars as pl

from config import *

from modules.quota import (
    load_quotas,
    generate_population
)
from modules.prompt import (
    load_template
)

from modules.runner import (
    run
)
from modules.output import (
    save,
    summary
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("poll_llm")


async def main():

    start = time.time()

    logger.info("Starting poll LLM simulation")
    logger.info(
        "Model=%s respondents=%s workers=%s",
        MODEL,
        N_RESPONDENTS,
        WORKERS
    )

    logger.info("Loading quotas")
    quotas = load_quotas(
        QUOTA_FILE
    )

    logger.info(
        "Loaded %s quota profiles",
        quotas.height
    )

    logger.info(
        "Generating synthetic population"
    )

    persons = generate_population(
        quotas,
        N_RESPONDENTS
    )

    logger.info(
        "Generated %s respondents",
        len(persons)
    )

    logger.info(
        "Loading prompt template"
    )

    template = load_template(
        PROMPT_FILE
    )

    logger.info(
        "Launching Ollama workers"
    )

    results = run(
        persons,
        template,
        MODEL,
        WORKERS
    )

    logger.info(
        "Received %s model responses",
        len(results)
    )

    logger.info(
        "Building dataframe"
    )

    df = pl.DataFrame(
        results
    )

    logger.info(
        "Saving results"
    )

    save(
        df,
        RESULT_FILE
    )

    logger.info(
        "Computing vote summary"
    )

    result_summary = summary(
        df
    )

    print(result_summary)

    logger.info(
        "Completed successfully in %.2fs",
        time.time() - start
    )


if __name__ == "__main__":
    asyncio.run(main())