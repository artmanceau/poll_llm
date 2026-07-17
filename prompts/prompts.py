import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from jinja2 import Template

from prompts.candidates import CANDIDATES

QUESTIONNAIRE_PATH = Path(__file__).with_name("questionnaire.json")


def load_template(path):

    with open(path) as f:
        return Template(
            f.read()
        )


def _enum_schema(name, values):
    """A one-property JSON schema whose value is constrained to ``values``."""
    return {
        "type": "object",
        "properties": {
            name: {"enum": values}
        },
        "required": [name],
        "additionalProperties": False,
    }


def _string_schema(name):
    return {
        "type": "object",
        "properties": {
            name: {"type": "string"}
        },
        "required": [name],
        "additionalProperties": False,
    }


# --------------------------------------------------------------------------- #
# Questionnaire definition
#
# The questionnaire is stored declaratively in ``questionnaire.json`` and
# compiled into ``Step``s here. Each step carries not just its question and
# schema but also its rules: how to normalise the raw answer (``transform``),
# whether it ends the conversation early (``stop``), and what to fill for the
# remaining fields when it does (``on_stop``). ``converse`` just walks the
# steps, so all the wording and branching lives in the JSON config.
# --------------------------------------------------------------------------- #

@dataclass
class Step:
    # ``key`` is both the JSON property the model must return and the field
    # name stored in the final record.
    key: str
    question: str
    schema: dict
    # Map the raw model answer to the stored value (e.g. "Oui" -> "Yes").
    transform: Callable = lambda v: v
    # Given the stored value, should the conversation end after this step?
    stop: Optional[Callable] = None
    # Values to fill for the not-yet-asked fields when ``stop`` fires.
    on_stop: dict = field(default_factory=dict)


def _build_schema(schema_spec, key, year, extra_vote_options):
    """Turn a JSON schema spec into a concrete JSON schema + option list.

    Returns ``(schema, options)`` where ``options`` is the resolved candidate
    list for a ``candidates`` step (used to render the question), else ``None``.
    """
    kind = schema_spec["type"]

    if kind == "candidates":
        candidates = random.sample(
            CANDIDATES[year],
            len(CANDIDATES[year]),
        )
        options = candidates + extra_vote_options
        return _enum_schema(key, options), options

    if kind == "enum":
        return _enum_schema(key, schema_spec["values"]), None

    if kind == "string":
        return _string_schema(key), None

    raise ValueError(f"Unknown schema type: {kind!r}")


def _make_transform(mapping):
    if not mapping:
        return lambda v: v
    return lambda v: mapping.get(v, v)


def build_questionnaire(year, path=QUESTIONNAIRE_PATH):
    """Compile the questionnaire config for a given election ``year``.

    Called once per persona, so the candidate list is shuffled per persona.
    ``{year}`` (in keys/questions/on_stop) and ``{options}`` (in the question
    of a ``candidates`` step) are substituted here.
    """
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    extra_vote_options = config.get("extra_vote_options", [])

    steps = []
    for raw in config["steps"]:
        key = raw["key"].format(year=year)

        schema, options = _build_schema(
            raw["schema"], key, year, extra_vote_options
        )

        options_text = (
            "\n".join(f"- {c}" for c in options) if options else ""
        )
        question = raw["question"].format(year=year, options=options_text)

        stop = None
        if "stop_when" in raw:
            # Bind the value now so the closure is not tied to the loop var.
            stop = lambda v, target=raw["stop_when"]: v == target

        on_stop = {
            k.format(year=year): value
            for k, value in raw.get("on_stop", {}).items()
        }

        steps.append(
            Step(
                key=key,
                question=question,
                schema=schema,
                transform=_make_transform(raw.get("transform")),
                stop=stop,
                on_stop=on_stop,
            )
        )

    return steps
