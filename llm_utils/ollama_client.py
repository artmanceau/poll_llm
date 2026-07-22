import json
import os
import hashlib

from diskcache import Cache
from loguru import logger

from llm_utils.utils import render
from prompts.prompts import build_questionnaire
from openai import OpenAI
import ollama
import mlflow

cache = Cache("./llm_cache")

_openai_client = None


def _openai_chat(model, messages, schema, name):
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url="https://llm.lab.sspcloud.fr/api/v1/"
        )

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


def _chat(model, client, messages, schema, name):
    try:
        provider = _openai_chat if client == 'openai' else _ollama_chat
        res = provider(model, messages, schema, name)
        return res
    except Exception as e:
        logger.error(f'Erreur sending request: {e}')
        # Return an empty compliant schema
        return {schema['required'][0] : None}


def converse(person, template, year, model, client, questionnaire=None):
    """Run a questionnaire as a sequential conversation and return the record.

    The flow is entirely driven by ``questionnaire`` -- a callable ``(year) ->
    [Step]`` (defaults to ``prompts.prompts.build_questionnaire``). Each step's
    question is asked in order, its answer normalised via ``step.transform``,
    and if ``step.stop`` fires the remaining fields are filled from
    ``step.on_stop`` and the conversation ends early. All branching rules thus
    live in the questionnaire definition, not here.
    """
    steps = (questionnaire or build_questionnaire)(year)

    result = {**person}

    # The rendered template carries the persona + election context.
    messages = [
            {
                "role": "system",
                "content": render(template, person, year),
            }
    ]

    for step in steps:
        messages.append({"role": "user", "content": step.question})

        answer = _chat(model, client, messages, step.schema, step.key)
        messages.append({"role": "assistant", "content": json.dumps(answer)})

        value = step.transform(answer[step.key])
        result[step.key] = value

        if step.stop and step.stop(value):
            result.update(step.on_stop)
            return result

    return result


def _make_key(model, year, person):
    payload = json.dumps(
        {"model": model, "year": year, "person": person},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def ask_with_mlflow(person, template, year, model, client, user_id=None, session_id=None, questionnaire=None):
    # Cache the whole conversation per persona (deterministic key, so it
    # hits despite the randomised candidate order inside a turn).
    with mlflow.tracing.context(session_id=session_id, user=user_id):
        return ask(person, template, year, model, client, user_id=user_id, session_id=session_id, questionnaire=None)


def ask(person, template, year, model, client, user_id=None, session_id=None, questionnaire=None):
    if session_id:
        i = session_id.split('_')[-1]
        if int(i) % 5 == 0:
            logger.debug(f'Processing at {session_id}')
    result = converse(person, template, year, model, client, questionnaire)
    return result
