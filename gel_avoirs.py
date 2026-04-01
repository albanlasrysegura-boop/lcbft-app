"""Module de recherche dans le registre national des gels des avoirs (DG Trésor)."""

import requests
from datetime import datetime

GEL_AVOIRS_JSON_URL = "https://gels-avoirs.dgtresor.gouv.fr/ApiPublic/api/v1/publication/derniere-publication-fichier-json"

_cache: dict = {"data": None, "date": None}


def telecharger_registre() -> list[dict]:
    """Télécharge le registre complet des gels des avoirs depuis la DG Trésor.

    Returns:
        Liste des entités du registre, ou liste avec un dict erreur.
    """
    if _cache["data"] is not None:
        return _cache["data"]

    try:
        response = requests.get(GEL_AVOIRS_JSON_URL, timeout=60)
        response.raise_for_status()
        data = response.json()
        entites = data["Publications"]["PublicationDetail"]
        _cache["data"] = entites
        _cache["date"] = datetime.now().isoformat()
        return entites
    except (requests.RequestException, KeyError) as e:
        return [{"erreur": f"Erreur téléchargement registre : {e}"}]


def _normaliser(texte: str) -> str:
    """Normalise un texte pour la comparaison (minuscules, sans accents simples)."""
    if not texte:
        return ""
    texte = texte.lower().strip()
    replacements = {
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "à": "a", "â": "a", "ä": "a",
        "ù": "u", "û": "u", "ü": "u",
        "ô": "o", "ö": "o",
        "î": "i", "ï": "i",
        "ç": "c", "ñ": "n",
    }
    for old, new in replacements.items():
        texte = texte.replace(old, new)
    return texte


def _extraire_champ(entite: dict, type_champ: str) -> str:
    """Extrait la valeur d'un champ depuis RegistreDetail."""
    for detail in entite.get("RegistreDetail", []):
        if detail.get("TypeChamp") == type_champ:
            valeurs = detail.get("Valeur", [])
            parties = []
            for val in valeurs:
                if isinstance(val, dict):
                    parties.extend(str(v) for v in val.values() if v)
            return " ".join(parties)
    return ""


def _extraire_texte_recherche(entite: dict) -> str:
    """Extrait tout le texte recherchable d'une entité."""
    parties = [entite.get("Nom", "")]

    for detail in entite.get("RegistreDetail", []):
        for val in detail.get("Valeur", []):
            if isinstance(val, dict):
                for v in val.values():
                    if v and isinstance(v, str):
                        parties.append(v)

    return " ".join(parties)


def _formater_resultat(entite: dict) -> dict:
    """Formate une entité du registre en résultat lisible."""
    prenom = _extraire_champ(entite, "PRENOM")
    alias = _extraire_champ(entite, "ALIAS")
    nationalite = _extraire_champ(entite, "NATIONALITE")
    motifs = _extraire_champ(entite, "MOTIFS")
    fondement = _extraire_champ(entite, "FONDEMENT_JURIDIQUE")
    mesure = _extraire_champ(entite, "MESURES")

    # Date de naissance
    date_naissance = ""
    for detail in entite.get("RegistreDetail", []):
        if detail.get("TypeChamp") == "DATE_DE_NAISSANCE":
            for val in detail.get("Valeur", []):
                jour = val.get("Jour", "")
                mois = val.get("Mois", "")
                annee = val.get("Annee", "")
                if annee:
                    date_naissance = f"{jour}/{mois}/{annee}" if jour and mois else annee

    return {
        "id_registre": entite.get("IdRegistre", ""),
        "nature": entite.get("Nature", ""),
        "nom": entite.get("Nom", ""),
        "prenom": prenom,
        "alias": alias,
        "nationalite": nationalite,
        "date_naissance": date_naissance,
        "fondement_juridique": fondement,
        "mesure": mesure,
        "motifs": motifs[:200] + "..." if len(motifs) > 200 else motifs,
    }


def rechercher_gel_avoirs(nom: str) -> list[dict]:
    """Recherche un nom dans le registre des gels des avoirs.

    Args:
        nom: Nom, prénom, ou dénomination à rechercher.

    Returns:
        Liste des correspondances trouvées.
    """
    entites = telecharger_registre()

    if entites and isinstance(entites[0], dict) and "erreur" in entites[0]:
        return entites

    nom_normalise = _normaliser(nom)
    termes = nom_normalise.split()
    resultats = []

    for entite in entites:
        if not isinstance(entite, dict):
            continue

        texte = _normaliser(_extraire_texte_recherche(entite))

        if all(terme in texte for terme in termes):
            resultats.append(_formater_resultat(entite))

    return resultats


def rechercher_gel_avoirs_multi(noms: list[str]) -> dict[str, list[dict]]:
    """Recherche plusieurs noms dans le registre des gels des avoirs."""
    telecharger_registre()
    return {nom: rechercher_gel_avoirs(nom) for nom in noms}
