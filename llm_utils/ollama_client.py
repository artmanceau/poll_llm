import json
import hashlib

from diskcache import Cache
from loguru import logger

from llm_utils.utils import render
from prompts.prompts import build_questionnaire
from openai import OpenAI
import ollama

cache = Cache("./llm_cache")

_openai_client = None


def _is_openai(model):
    return model.startswith(("gpt", "o1", "o3", "o4", "chatgpt"))


def _openai_chat(model, messages, schema, name):
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()

    response = _openai_client.chat.completions.create(
        model=model,
        temperature=0.8,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": name,
                "strict": True,
                "schema": schema,
            },
        },
        messages=messages,
    )
    return json.loads(response.choices[0].message.content)


def _ollama_chat(model, messages, schema, name):
    response = ollama.chat(
        model=model,
        format=schema,
        think=False,
        messages=messages,
        options={
            "temperature": 0.8
        },
    )
    return json.loads(response["message"]["content"])


def _chat(model, messages, schema, name):
    provider = _openai_chat if _is_openai(model) else _ollama_chat
    return provider(model, messages, schema, name)


def converse(person, template, year, model, questionnaire=None):
    """Run a questionnaire as a sequential conversation and return the record.

    The flow is entirely driven by ``questionnaire`` -- a callable ``(year) ->
    [Step]`` (defaults to ``prompts.prompts.build_questionnaire``). Each step's
    question is asked in order, its answer normalised via ``step.transform``,
    and if ``step.stop`` fires the remaining fields are filled from
    ``step.on_stop`` and the conversation ends early. All branching rules thus
    live in the questionnaire definition, not here.
    """
    steps = (questionnaire or build_questionnaire)(year)

    logger.debug(f"Starting conversation for {person}")

    result = {**person}

    # The rendered template carries the persona + election context.
    messages = [
        {
            "role": "system",
            "content": render(template, person, year),
        }
    ]

    for step in steps:
        logger.debug(f"Q[{step.key}]: {step.question}")
        messages.append({"role": "user", "content": step.question})

        answer = _chat(model, messages, step.schema, step.key)
        messages.append({"role": "assistant", "content": json.dumps(answer)})

        value = step.transform(answer[step.key])
        result[step.key] = value
        logger.debug(f"A[{step.key}]: {value}")

        if step.stop and step.stop(value):
            logger.info(
                f"{person} stopped at '{step.key}' -- ending conversation"
            )
            result.update(step.on_stop)
            return result

    logger.debug(f"Completed conversation for {person}: {result}")

    return result


def _make_key(model, year, person):
    payload = json.dumps(
        {"model": model, "year": year, "person": person},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def ask(person, template, year, model, questionnaire=None):
    # Cache the whole conversation per persona (deterministic key, so it
    # hits despite the randomised candidate order inside a turn).
    key = _make_key(model, year, person)

    cached = cache.get(key)
    if cached:
        logger.debug(f"cache hit for {person}")
        return {**person, **cached}

    result = converse(person, template, year, model, questionnaire)

    # Store only the answer fields (persona is re-merged on read).
    answer = {k: v for k, v in result.items() if k not in person}
    cache.set(key, answer, expire=60 * 60 * 24 * 30)

    return result
