import json
import hashlib
from openai import OpenAI
from diskcache import Cache
from loguru import logger
from llm_utils.utils import get_vote_schema, render


client = OpenAI()

cache = Cache("./openai_cache")


def make_key(model, prompt):
    return hashlib.sha256(
        f"{model}:{prompt}".encode()
    ).hexdigest()


def ask(
    person,
    template,
    year,
    model="gpt-4.1-mini"
):
    prompt = render(
        template,
        person,
        year
    )

    key = make_key(
        model,
        prompt
    )

    cached = cache.get(key)

    if cached:
        logger.debug("cache hit")
        return {
            **person,
            **cached
        }

    logger.debug(
        f"processing {person}"
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0.8,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "vote",
                "strict": True,
                "schema": get_vote_schema(year)
            }
        },
        messages=[
            {
                "role": "system",
                "content": ""
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    answer = json.loads(
        response.choices[0]
        .message
        .content
    )

    cache.set(
        key,
        answer,
        expire=60 * 60 * 24 * 30
    )

    return {
        **person,
        **answer
    }
