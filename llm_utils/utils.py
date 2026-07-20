from prompts.candidates import CANDIDATES
import random as random


def render(template, person, year):
    return template.render(
        **person,
        YEAR=year,
        CANDIDATES=random.sample(
            CANDIDATES[year],
            len(CANDIDATES[year])
        )
    )


def get_vote_schema(year):
    return {
        "type": "object",
        "properties": {
            f"vote{year}": {
                "type": "string",
                "enum": CANDIDATES[year]
            },
            "raison": {
                "type": "string"
            }
        },
        "required": [
            f"vote{year}",
            "raison"
        ],
        "additionalProperties": False
    }