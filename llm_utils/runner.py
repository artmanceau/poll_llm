from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)
from llm_utils.ollama_client import ask


def run(persons, template, year, model, client, workers):
    results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(ask, p, template, year, model, client)
            for p in persons.iter_rows(named=True)
        ]

        for future in as_completed(futures):
            results.append(future.result())

    return results