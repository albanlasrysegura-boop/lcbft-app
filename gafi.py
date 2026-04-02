"""Module GAFI/FATF : vérification des pays à risque.

Listes mises à jour au 13 février 2026 (dernière session plénière GAFI).
Source : https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html
"""

# Liste noire GAFI - Juridictions à haut risque faisant l'objet d'un appel à l'action
LISTE_NOIRE = [
    "Iran",
    "Corée du Nord",
    "Myanmar",
]

# Liste grise GAFI - Juridictions sous surveillance renforcée (février 2026)
LISTE_GRISE = [
    "Algérie",
    "Angola",
    "Bolivie",
    "Haïti",
    "Koweït",
    "Laos",
    "Liban",
    "Mali",
    "Monaco",
    "Namibie",
    "Népal",
    "Papouasie-Nouvelle-Guinée",
    "Soudan du Sud",
    "Syrie",
    "Tanzanie",
    "Émirats arabes unis",
    "Îles Vierges britanniques",
    "Yémen",
]

# Correspondances noms alternatifs / anglais → français
_ALIASES: dict[str, str] = {
    "iran": "Iran",
    "north korea": "Corée du Nord",
    "coree du nord": "Corée du Nord",
    "dprk": "Corée du Nord",
    "myanmar": "Myanmar",
    "burma": "Myanmar",
    "birmanie": "Myanmar",
    "algeria": "Algérie",
    "algerie": "Algérie",
    "angola": "Angola",
    "bolivia": "Bolivie",
    "bolivie": "Bolivie",
    "haiti": "Haïti",
    "kuwait": "Koweït",
    "koweit": "Koweït",
    "laos": "Laos",
    "lao pdr": "Laos",
    "lebanon": "Liban",
    "liban": "Liban",
    "mali": "Mali",
    "monaco": "Monaco",
    "namibia": "Namibie",
    "namibie": "Namibie",
    "nepal": "Népal",
    "papua new guinea": "Papouasie-Nouvelle-Guinée",
    "papouasie-nouvelle-guinee": "Papouasie-Nouvelle-Guinée",
    "south sudan": "Soudan du Sud",
    "soudan du sud": "Soudan du Sud",
    "syria": "Syrie",
    "syrie": "Syrie",
    "tanzania": "Tanzanie",
    "tanzanie": "Tanzanie",
    "uae": "Émirats arabes unis",
    "united arab emirates": "Émirats arabes unis",
    "emirats arabes unis": "Émirats arabes unis",
    "british virgin islands": "Îles Vierges britanniques",
    "iles vierges britanniques": "Îles Vierges britanniques",
    "bvi": "Îles Vierges britanniques",
    "yemen": "Yémen",
}


def _normaliser(texte: str) -> str:
    texte = texte.lower().strip()
    for old, new in {"é": "e", "è": "e", "ê": "e", "ë": "e",
                      "à": "a", "â": "a", "ù": "u", "û": "u",
                      "ô": "o", "î": "i", "ï": "i", "ç": "c"}.items():
        texte = texte.replace(old, new)
    return texte


def verifier_pays_gafi(pays: str) -> dict:
    """Vérifie si un pays est sur les listes GAFI.

    Args:
        pays: Nom du pays (français ou anglais).

    Returns:
        Dictionnaire avec le statut du pays.
    """
    pays_lower = pays.lower().strip()
    pays_norm = _normaliser(pays)

    # Résoudre le nom canonique
    nom_canon = _ALIASES.get(pays_lower) or _ALIASES.get(pays_norm)

    if not nom_canon:
        # Recherche partielle
        for alias, canon in _ALIASES.items():
            if pays_norm in _normaliser(alias) or _normaliser(alias) in pays_norm:
                nom_canon = canon
                break

    if nom_canon and nom_canon in LISTE_NOIRE:
        return {
            "pays": nom_canon,
            "liste": "LISTE NOIRE",
            "risque": "TRÈS ÉLEVÉ",
            "description": "Juridiction à haut risque - Appel à l'action du GAFI. "
                           "Contre-mesures recommandées.",
        }
    elif nom_canon and nom_canon in LISTE_GRISE:
        return {
            "pays": nom_canon,
            "liste": "LISTE GRISE",
            "risque": "ÉLEVÉ",
            "description": "Juridiction sous surveillance renforcée du GAFI. "
                           "Vigilance complémentaire requise.",
        }
    else:
        return {
            "pays": pays,
            "liste": "AUCUNE",
            "risque": "STANDARD",
            "description": "Ce pays n'est pas sur les listes GAFI.",
        }


def get_listes_gafi() -> dict:
    """Retourne les listes GAFI complètes."""
    return {
        "liste_noire": LISTE_NOIRE,
        "liste_grise": LISTE_GRISE,
        "date_mise_a_jour": "13 février 2026",
        "source": "https://www.fatf-gafi.org/en/countries/black-and-grey-lists.html",
    }
