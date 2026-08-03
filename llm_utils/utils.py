from prompts.candidates import CANDIDATES
from pathlib import Path
import random as random


def render(template, person, year):
    candidates = random.sample(CANDIDATES[year], len(CANDIDATES[year]))
    context = Path(f"prompts/contexts/pres_{year}.jinja2").read_text()
    return template.render(**person, YEAR=year, CANDIDATES=candidates, CONTEXT=context)


def get_vote_schema(year):
    return {
        "type": "object",
        "properties": {
            f"vote{year}": {"type": "string", "enum": CANDIDATES[year]},
            "raison": {"type": "string"},
        },
        "required": [f"vote{year}", "raison"],
        "additionalProperties": False,
    }
