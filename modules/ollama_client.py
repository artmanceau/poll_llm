import json
import ollama

vote_schema = {
    "type": "object",
    "properties": {
        "vote": {
            "type": "string",
            "enum": [
                "Nathalie Arthaud",
                "Jean-Luc Mélenchon",
                "Fabien Roussel",
                "Marine Tondelier",
                "Raphaël Glucksmann",
                "Gabriel Attal",
                "Édouard Philippe",
                "Bruno Retailleau",
                "Nicolas Dupont-Aignan",
                "Marine Le Pen",
                "Éric Zemmour",
                "Abstention",
                "Blanc"
            ]
        }
    },
    "required": [
        "vote"
    ]
}


def ask(
    person,
    template,
    model
):

    prompt = template.render(
        **person
    )

    response = ollama.chat(
        model=model,
        format=vote_schema,
        messages=[
            {
                "role": "system",
                "content": """
Tu es un institut de sondage.
Répond uniquement en JSON.
"""
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

    return {
        **person,
        **answer
    }