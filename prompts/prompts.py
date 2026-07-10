from jinja2 import Template


def load_template(path):

    with open(path) as f:
        return Template(
            f.read()
        )
