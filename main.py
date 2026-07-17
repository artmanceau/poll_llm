import asyncio
from loguru import logger
import time
import polars as pl
from dotenv import load_dotenv
import s3fs
import posixpath
from pathlib import Path
import json

from quotas.get_quotas_data import (
    get_quotas,
)
from llm_utils.runner import (
    run
)
from prompts.prompts import (
    load_template,
    QUESTIONNAIRE_PATH,
)
from prompts.candidates import (
    CANDIDATES
)

RESULT_PATH = "s3://arthurmanceau/poll_llm/results/"
PROMPT_PATH = "s3://arthurmanceau/poll_llm/llm_prompts/"


def save_prompt_artifacts(template, version):
    """Persist the prompt template and questionnaire config to S3 for audit."""
    fs = s3fs.S3FileSystem(
        profile="default",
        endpoint_url="https://minio.lab.sspcloud.fr",
        client_kwargs={"region_name": "us-east-1"},
    )

    artifacts = {
        "prompt_template.jinja2": template.render(),
        "questionnaire.json": QUESTIONNAIRE_PATH.read_text(encoding="utf-8"),
    }

    for name, content in artifacts.items():
        path = posixpath.join(PROMPT_PATH, version, name)
        logger.debug(f"Saving audit artifact to {path}")
        with fs.open(path, "w", encoding="utf-8") as f:
            f.write(content)

    logger.success(
        f"Saved prompt + questionnaire for audit under "
        f"{posixpath.join(PROMPT_PATH, version)}",
    )


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

    config_path = Path("config/poll.json")
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    logger.info("Starting poll LLM simulation")
    logger.debug(
        f"Model={config['model']} respondents={config['n_respondants']} workers={config['workers']}",
    )
    logger.debug(
        f"Election présdientielle de {config['year']} (candidats: {CANDIDATES[config['year']]})",
    )
    logger.info(
        "Generating synthetic population based on quotas"
    )

    # 1. Get representative sample
    quotas = get_quotas(config['n_respondants'])

    logger.success(
        f"Generated {quotas.height} quota profiles (data from 2023)",
    )

    # 2. Make LLMs vote
    template = load_template(
        config['prompt_file']
    )

    logger.debug(
        "Launching Ollama workers"
    )

    results = run(
        quotas,
        template,
        config['year'],
        config['model'],
        config['client'],
        config['workers']
    )

    # 3. Save and process results
    logger.info(
        f"Received {len(results)} model responses",
    )

    detailed = pl.DataFrame(
        results
    )

    summary = get_summary(
        detailed, config['year']
    )

    logger.success(config['year'])
    logger.success(summary)

    # Sample is stored
    detailed_path = posixpath.join(
        "s3://arthurmanceau",
        "poll_llm",
        "results",
        config['version'],
        config['model'],
        str(config['year']),
        str(config['n_respondants']),
        "detailed.csv",
    )
    detailed.write_csv(
        detailed_path,
        storage_options={
            "aws_endpoint_url": "https://minio.lab.sspcloud.fr",
            "aws_region": "us-east-1",
        },
        credential_provider=pl.CredentialProviderAWS(
            profile_name="default",
            region_name="us-east-1",
        ),)

    # Aggregated results
    summary_path = posixpath.join(
        "s3://arthurmanceau",
        "poll_llm",
        "results",
        config['version'],
        config['model'],
        str(config['year']),
        str(config['n_respondants']),
        "summary.csv",
    )
    summary.write_csv(
        summary_path,
        storage_options={
            "aws_endpoint_url": "https://minio.lab.sspcloud.fr",
            "aws_region": "us-east-1",
        },
        credential_provider=pl.CredentialProviderAWS(
            profile_name="default",
            region_name="us-east-1",
        ),)

    # Save prompt + questionnaire for audit
    save_prompt_artifacts(template, config['version'])

    logger.info(f"Completed successfully in {time.time() - start:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
