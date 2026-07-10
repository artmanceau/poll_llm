import json
import ollama
from loguru import logger
from llm_utils.utils import render, get_vote_schema


def ask(
    person,
    template,
    year,
    model
):

    prompt = render(
        template,
        person,
        year,
    )

    logger.debug(f"Processing vote for {person}")

    response = ollama.chat(
        model=model,
        format=get_vote_schema(year),
        messages=[
            {
                "role": "system",
                "content": """"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        options={
            "temperature": 0.8
        }
    )

    answer = json.loads(
        response["message"]["content"]
    )

    logger.debug(f"Processing vote for {person}. Vote: {answer}")

    return {
        **person,
        **answer
    }