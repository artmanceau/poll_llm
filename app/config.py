import colorsys
import polars as pl

BUCKET_ROOT = "s3://arthurmanceau/poll_llm/results"


CANDIDATES = {
    "2022": [
        "Nathalie Arthaud (Lutte ouvrière)",
        "Fabien Roussel (Parti communiste français)",
        "Emmanuel Macron (La République en marche)",
        "Jean Lassalle (Résistons)",
        "Marine Le Pen (Rassemblement national)",
        "Éric Zemmour (Reconquête)",
        "Jean-Luc Mélenchon (La France insoumise)",
        "Anne Hidalgo (Parti Socialiste)",
        "Yannick Jadot (Europe Écologie Les Verts)",
        "Valérie Pécresse (Les Républicains)",
        "Philippe Poutou (Nouveau Parti anticapitaliste)",
        "Nicolas Dupont-Aignan (Debout la France)",
    ],
    "2027": [
        "Nathalie Arthaud (Lutte ouvrière)",
        "Fabien Roussel (Parti communiste français)",
        "Jean-Luc Mélenchon (La France Insoumise)",
        "Marine Tondelier (Les Écologistes)",
        "Raphaël Glucksmann (Parti socialiste / Place Publique)",
        "Gabriel Attal (Ensemble)",
        "Édouard Philippe (Horizon)",
        "Bruno Retailleau (Les Républicains)",
        "Nicolas Dupont-Aignan (Debout la France)",
        "Marine Le Pen (Rassemblement national)",
        "Éric Zemmour (Reconquête)",
    ],
}


BLOCS = {
    2027: {
        "G": [
            "Nathalie Arthaud (Lutte ouvrière)",
            "Fabien Roussel (Parti communiste français)",
            "Jean-Luc Mélenchon (La France Insoumise)",
        ],
        "CG": [
            "Marine Tondelier (Les Écologistes)",
            "Raphaël Glucksmann (Parti socialiste / Place Publique)",
        ],
        "C": [
            "Gabriel Attal (Ensemble)",
            "Édouard Philippe (Horizon)",
        ],
        "CD": [
            "Bruno Retailleau (Les Républicains)",
        ],
        "D": [
            "Nicolas Dupont-Aignan (Debout la France)",
            "Marine Le Pen (Rassemblement national)",
            "Éric Zemmour (Reconquête)",
        ],
    },
    2022: {
        "G": [
            "Nathalie Arthaud (Lutte ouvrière)",
            "Fabien Roussel (Parti communiste français)",
            "Philippe Poutou (Nouveau Parti anticapitaliste)",
            "Jean-Luc Mélenchon (La France insoumise)",
        ],
        "CG": [
            "Anne Hidalgo (Parti Socialiste)",
            "Yannick Jadot (Europe Écologie Les Verts)",
        ],
        "C": [
            "Emmanuel Macron (La République en marche)",
            "Jean Lassalle (Résistons)",
        ],
        "CD": [
            "Valérie Pécresse (Les Républicains)",
        ],
        "D": [
            "Nicolas Dupont-Aignan (Debout la France)",
            "Marine Le Pen (Rassemblement national)",
            "Éric Zemmour (Reconquête)",
        ],
    },
}


def candidate_to_bloc(year):
    return {
        candidate: bloc
        for bloc, candidates in BLOCS[year].items()
        for candidate in candidates
    }


# Total Gauche (TG) / Total Droite (TD): which blocs sum into each side.
BLOC_SIDES = {"TG": ["G", "CG"], "TD": ["CD", "D"], "C": ["C"]}


def candidate_to_side(year):
    return {
        candidate: side
        for side, blocs in BLOC_SIDES.items()
        for bloc in blocs
        for candidate in BLOCS[year][bloc]
    }


CANDIDATE_COLORS = {
    "Nathalie Arthaud (Lutte ouvrière)": "#B22222",
    "Philippe Poutou (Nouveau Parti anticapitaliste)": "#E53935",
    "Fabien Roussel (Parti communiste français)": "#C00000",
    "Jean-Luc Mélenchon (La France insoumise)": "#C62828",
    "Jean-Luc Mélenchon (La France Insoumise)": "#C62828",
    "Anne Hidalgo (Parti Socialiste)": "#E91E63",
    "Raphaël Glucksmann (Parti socialiste / Place Publique)": "#E91E63",
    "Yannick Jadot (Europe Écologie Les Verts)": "#4CAF50",
    "Marine Tondelier (Les Écologistes)": "#4CAF50",
    "Emmanuel Macron (La République en marche)": "#F4C542",
    "Gabriel Attal (Ensemble)": "#F4C542",
    "Édouard Philippe (Horizon)": "#F4C542",
    "Valérie Pécresse (Les Républicains)": "#0055A4",
    "Bruno Retailleau (Les Républicains)": "#0055A4",
    "Jean Lassalle (Résistons)": "#4E342E",
    "Nicolas Dupont-Aignan (Debout la France)": "#1E88E5",
    "Marine Le Pen (Rassemblement national)": "#0B3D91",
    "Éric Zemmour (Reconquête)": "#5C0011",
    "Abstention": "#F00000",
    "Vote blanc ou nul": "#F00000",
}


BLOC_COLORS = {
    "G": "#B22222",
    "CG": "#E91E63",
    "C": "#F4C542",
    "CD": "#0055A4",
    "D": "#0B3D91",
}


SOURCE_PATTERNS = {
    "LLM poll": "",
    "Résultat officiel": "/",
    "Sondages tendance": ".",
}


def adjust_color(hex_color, factor):
    hex_color = hex_color.replace("#", "")

    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255

    h, la, s = colorsys.rgb_to_hls(r, g, b)

    la = max(0, min(1, la * factor))

    r, g, b = colorsys.hls_to_rgb(h, la, s)

    return "#{:02x}{:02x}{:02x}".format(
        int(r * 255),
        int(g * 255),
        int(b * 255),
    )


sondages_smoothed = pl.DataFrame(
    {
        "vote2022": CANDIDATES["2022"],
        "pvote": [
            0.5555522914642451,
            0.999999999999226,
            2.6915058730916215,
            17.16201220054569,
            2.0511403432017308,
            4.906673937286057,
            26.22890349406319,
            8.371935740613074,
            2.709478368598444,
            2.3018239511475214,
            23.1476141442254,
            8.886892008663699,
        ],
        "source": ["sondages"] * len(CANDIDATES["2022"]),
    }
)


def build_bar_colors():
    result = {}

    for candidate, color in CANDIDATE_COLORS.items():
        result[(candidate, "LLM poll")] = adjust_color(
            color,
            1.2,
        )

        result[(candidate, "Résultat officiel")] = adjust_color(
            color,
            1.0,
        )

        result[(candidate, "Sondages tendance")] = adjust_color(
            color,
            0.8,
        )

    return result
