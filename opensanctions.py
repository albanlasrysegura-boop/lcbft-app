"""Module de recherche OpenSanctions (PPE + Sanctions internationales).

Couvre : sanctions UE, ONU, OFAC, UK, + 100 autres listes.
Inclut les Personnes Politiquement Exposées (PPE/PEP).
Nécessite une clé API (essai gratuit 30 jours sur opensanctions.org).
"""

import requests

API_BASE = "https://api.opensanctions.org"


def rechercher_opensanctions(
    nom: str,
    api_key: str,
    limit: int = 10,
    dataset: str = "default",
) -> list[dict]:
    """Recherche un nom dans OpenSanctions (sanctions + PPE).

    Args:
        nom: Nom à rechercher.
        api_key: Clé API OpenSanctions.
        limit: Nombre max de résultats.
        dataset: Dataset à interroger (default, peps, sanctions...).

    Returns:
        Liste de correspondances.
    """
    if not api_key:
        return [{"erreur": "Clé API OpenSanctions non configurée. "
                 "Obtenez-en une sur https://www.opensanctions.org/api/"}]

    url = f"{API_BASE}/search/{dataset}"
    params = {"q": nom, "limit": limit}
    headers = {"Authorization": f"ApiKey {api_key}"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return [{"erreur": f"Erreur API OpenSanctions : {e}"}]

    resultats = []
    for result in data.get("results", []):
        props = result.get("properties", {})

        # Déterminer les catégories de risque
        topics = result.get("topics", [])
        est_ppe = any("role" in t or "pep" in t.lower() for t in topics)
        est_sanctionne = any("sanction" in t for t in topics)
        est_crime = any("crime" in t for t in topics)

        # Déterminer les datasets sources
        datasets = result.get("datasets", [])

        resultats.append({
            "id": result.get("id", ""),
            "nom": " ".join(props.get("name", [])),
            "type": result.get("schema", ""),
            "score": result.get("score", 0),
            "pays": ", ".join(props.get("country", [])),
            "nationalite": ", ".join(props.get("nationality", [])),
            "date_naissance": ", ".join(props.get("birthDate", [])),
            "ppe": est_ppe,
            "sanctionne": est_sanctionne,
            "crime": est_crime,
            "topics": ", ".join(topics),
            "datasets": ", ".join(datasets),
            "description": " | ".join(props.get("notes", []))[:200],
            "alias": ", ".join(props.get("alias", [])),
            "position": ", ".join(props.get("position", [])),
        })

    return resultats


def rechercher_ppe(nom: str, api_key: str, limit: int = 10) -> list[dict]:
    """Recherche spécifique dans la base PPE."""
    return rechercher_opensanctions(nom, api_key, limit=limit, dataset="peps")


def rechercher_sanctions(nom: str, api_key: str, limit: int = 10) -> list[dict]:
    """Recherche spécifique dans les listes de sanctions."""
    return rechercher_opensanctions(nom, api_key, limit=limit, dataset="sanctions")
