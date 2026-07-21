# Candidats à l'élection présidentielle de 2027
candidates_2027 = [
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
    "Abstention",
    "Vote blanc ou nul"
]

# Candidats à l'élection présidentielle de 2022
candidates_2022 = [
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
    "Abstention",
    "Vote blanc ou nul"
]

candidates_2017 = [
    "Nathalie Arthaud (Lutte ouvrière)",
    "Fabien Roussel (Parti communiste français)",
    "Emmanuel Macron (La République en marche)",
    "Jean Lassalle (Résistons)",
    "Marine Le Pen (Rassemblement national)",
    "Éric Zemmour (Reconquête)",
    "Jean-Luc Mélenchon (La France insoumise)",
    "Benoît Hamon (Parti Socialiste)",
    "François Fillon (Les Républicains)",
    "Philippe Poutou (Nouveau Parti anticapitaliste)",
    "Nicolas Dupont-Aignan (Debout la France)",
    "François Asselineau (Union populaire et republicaine)",
    "Jacques Cheminade (Solidarités et progrès)",
    "Abstention",
    "Vote blanc ou nul"
]

CANDIDATES = {
    2017 : candidates_2017,
    2022: candidates_2022,
    2027: candidates_2027
}

CANDIDATES_T2 = {
    2017 : {
        't2hyp1': [
                "Emmanuel Macron (La République en marche)", 
                "Marine Le Pen (Rassemblement national)", 
                "Abstention",
                "Vote blanc ou nul"
            ],
        't2hyp2': [
            "Emmanuel Macron (La République en marche)",
            "Jean-Luc Mélenchon (La France insoumise)",
            "Abstention",
            "Vote blanc ou nul"
        ],
        't2hyp3': [
            "Marine Le Pen (Rassemblement national)", 
            "Jean-Luc Mélenchon (La France insoumise)",
            "Abstention",
            "Vote blanc ou nul"
        ]
    },
    2022 : {
        't2hyp1': [
                "Emmanuel Macron (La République en marche)", 
                "Marine Le Pen (Rassemblement national)", 
                "Abstention",
                "Vote blanc ou nul"
            ],
        't2hyp2': [
            "Emmanuel Macron (La République en marche)",
            "Jean-Luc Mélenchon (La France insoumise)",
            "Abstention",
            "Vote blanc ou nul"
        ],
        't2hyp3': [
            "Marine Le Pen (Rassemblement national)", 
            "Jean-Luc Mélenchon (La France insoumise)",
            "Abstention",
            "Vote blanc ou nul"
        ]
    }
}