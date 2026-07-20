from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)
from llm_utils.ollama_client import ask_with_mlflow, ask
import mlflow
from datetime import datetime, timezone

ML_FLOW_TRACKING = True


def run(persons, template, year, model, client, workers):

    results = []

    if ML_FLOW_TRACKING:
        # Enable auto-tracing for OpenAI
        mlflow.openai.autolog()

        # Set a tracking URI and an experiment
        mlflow.set_tracking_uri("https://user-arthurmanceau-mlflow.user.lab.sspcloud.fr")
        mlflow.set_experiment("Poll LLM")

    ts = datetime.now(timezone.utc)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                ask_with_mlflow if ML_FLOW_TRACKING else ask,
                p,
                template,
                year,
                model,
                client,
                user_id=f"runner_{ts:%Y%m%dT%H%M%S_%f}",
                session_id=f'runner_{ts:%Y%m%dT%H%M%S_%f}_persona_{i}')
            for i, p in enumerate(persons.iter_rows(named=True))
        ]

        for future in as_completed(futures):
            results.append(future.result())

    return results
