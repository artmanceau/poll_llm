from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed
)


def run(
    persons,
    template,
    model,
    workers
):

    results = []
    
    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:

        futures = [
            executor.submit(
                __import__(
                    "modules.ollama_client",
                    fromlist=["ask"]
                ).ask,
                p,
                template,
                model
            )
            for p in persons
        ]

        for future in as_completed(futures):
            results.append(
                future.result()
            )

    return results