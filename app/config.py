import colorsys
import polars as pl

BUCKET_ROOT = "s3://arthurmanceau/poll_llm/results"


CANDIDATES = [
    "Nathalie Arthaud (Lutte ouvrière)",
    "Philippe Poutou (Nouveau Parti anticapitaliste)",
    "Fabien Roussel (Parti communiste français)",
    "Jean-Luc Mélenchon (La France insoumise)",
    "Anne Hidalgo (Parti Socialiste)",
    "Yannick Jadot (Europe Écologie Les Verts)",
    "Emmanuel Macron (La République en marche)",
    "Valérie Pécresse (Les Républicains)",
    "Jean Lassalle (Résistons)",
    "Nicolas Dupont-Aignan (Debout la France)",
    "Marine Le Pen (Rassemblement national)",
    "Éric Zemmour (Reconquête)",
]


BLOCS = {
    "G": [
        "Nathalie Arthaud (Lutte ouvrière)",
        "Philippe Poutou (Nouveau Parti anticapitaliste)",
        "Fabien Roussel (Parti communiste français)",
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
}


CANDIDATE_TO_BLOC = {
    candidate: bloc
    for bloc, candidates in BLOCS.items()
    for candidate in candidates
}


# Total Gauche (TG) / Total Droite (TD): which blocs sum into each side.
# A bloc absent from every list (here the Centre "C") is excluded from both
# totals. To fold the centre into a side, add "C" to the relevant list.
BLOC_SIDES = {
    "TG": ["G", "CG"],
    "TD": ["CD", "D"],
}


CANDIDATE_TO_SIDE = {
    candidate: side
    for side, blocs in BLOC_SIDES.items()
    for bloc in blocs
    for candidate in BLOCS[bloc]
}


CANDIDATE_COLORS = {
    "Nathalie Arthaud (Lutte ouvrière)": "#B22222",
    "Philippe Poutou (Nouveau Parti anticapitaliste)": "#E53935",
    "Fabien Roussel (Parti communiste français)": "#C00000",
    "Jean-Luc Mélenchon (La France insoumise)": "#C62828",
    "Anne Hidalgo (Parti Socialiste)": "#E91E63",
    "Yannick Jadot (Europe Écologie Les Verts)": "#4CAF50",
    "Emmanuel Macron (La République en marche)": "#F4C542",
    "Valérie Pécresse (Les Républicains)": "#0055A4",
    "Jean Lassalle (Résistons)": "#4E342E",
    "Nicolas Dupont-Aignan (Debout la France)": "#1E88E5",
    "Marine Le Pen (Rassemblement national)": "#0B3D91",
    "Éric Zemmour (Reconquête)": "#5C0011",
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

    h, l, s = colorsys.rgb_to_hls(r, g, b)

    l = max(0, min(1, l * factor))

    r, g, b = colorsys.hls_to_rgb(h, l, s)

    return "#{:02x}{:02x}{:02x}".format(
        int(r * 255),
        int(g * 255),
        int(b * 255),
    )


sondages_smoothed = pl.DataFrame(
    {
        f"vote2022": CANDIDATES,
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
        "source": ["sondages"] * len(CANDIDATES),
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