"""Module de recherche web pour la détection d'informations défavorables (adverse media).

Utilise l'API Google Custom Search (gratuit jusqu'à 100 recherches/jour).
Alternative : DuckDuckGo (sans clé API).
"""

import requests
import re
from urllib.parse import quote_plus

# Mots-clés négatifs pour détecter les informations défavorables
MOTS_CLES_NEGATIFS = [
    "fraude", "fraud", "blanchiment", "money laundering",
    "corruption", "condamné", "condamnation", "convicted",
    "mis en examen", "enquête", "investigation",
    "escroquerie", "scam", "arnaque",
    "sanctions", "sanctionné", "embargo",
    "terrorisme", "terrorism", "financement du terrorisme",
    "détournement", "embezzlement", "abus de biens sociaux",
    "faillite", "bankruptcy", "liquidation judiciaire",
    "trafic", "trafficking", "contrebande",
    "évasion fiscale", "tax evasion", "paradis fiscal",
    "garde à vue", "interpellé", "arrêté", "arrested",
    "procès", "tribunal", "jugement", "poursuites",
    "amende", "pénalité", "fine", "penalty",
]


def rechercher_google(
    nom: str,
    api_key: str = "",
    cx: str = "",
    nb_resultats: int = 10,
) -> list[dict]:
    """Recherche Google Custom Search pour informations défavorables.

    Args:
        nom: Nom à rechercher.
        api_key: Clé API Google Custom Search.
        cx: ID du moteur de recherche personnalisé.
        nb_resultats: Nombre de résultats.

    Returns:
        Liste de résultats web avec analyse.
    """
    if api_key and cx:
        return _recherche_google_api(nom, api_key, cx, nb_resultats)
    else:
        return _recherche_duckduckgo(nom, nb_resultats)


def _recherche_google_api(
    nom: str, api_key: str, cx: str, nb_resultats: int
) -> list[dict]:
    """Recherche via Google Custom Search API."""
    # Ajouter des termes de vigilance à la recherche
    query = f'"{nom}" (fraude OR blanchiment OR condamnation OR sanctions OR escroquerie OR corruption)'

    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": min(nb_resultats, 10),
        "lr": "lang_fr",
    }

    try:
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return [{"erreur": f"Erreur Google Search : {e}"}]

    resultats = []
    for item in data.get("items", []):
        titre = item.get("title", "")
        snippet = item.get("snippet", "")
        texte = f"{titre} {snippet}".lower()

        mots_trouves = [m for m in MOTS_CLES_NEGATIFS if m in texte]

        resultats.append({
            "titre": titre,
            "url": item.get("link", ""),
            "extrait": snippet,
            "mots_cles_negatifs": ", ".join(mots_trouves),
            "nb_alertes": len(mots_trouves),
            "source": "Google",
        })

    return resultats


def _recherche_duckduckgo(nom: str, nb_resultats: int) -> list[dict]:
    """Recherche via DuckDuckGo (sans clé API)."""
    query = f"{nom} fraude blanchiment condamnation sanctions"

    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return [{"erreur": f"Erreur DuckDuckGo : {e}"}]

    resultats = []

    # Résultat principal
    if data.get("AbstractText"):
        texte = data["AbstractText"].lower()
        mots_trouves = [m for m in MOTS_CLES_NEGATIFS if m in texte]
        resultats.append({
            "titre": data.get("Heading", ""),
            "url": data.get("AbstractURL", ""),
            "extrait": data["AbstractText"][:300],
            "mots_cles_negatifs": ", ".join(mots_trouves),
            "nb_alertes": len(mots_trouves),
            "source": "DuckDuckGo",
        })

    # Résultats associés
    for topic in data.get("RelatedTopics", [])[:nb_resultats]:
        if isinstance(topic, dict) and topic.get("Text"):
            texte = topic["Text"].lower()
            mots_trouves = [m for m in MOTS_CLES_NEGATIFS if m in texte]
            resultats.append({
                "titre": topic.get("Text", "")[:100],
                "url": topic.get("FirstURL", ""),
                "extrait": topic.get("Text", "")[:300],
                "mots_cles_negatifs": ", ".join(mots_trouves),
                "nb_alertes": len(mots_trouves),
                "source": "DuckDuckGo",
            })

    if not resultats:
        resultats.append({
            "info": f"Recherche web effectuée pour '{nom}'. "
                    "Aucun résultat structuré via DuckDuckGo. "
                    "Pour de meilleurs résultats, configurez une clé API Google.",
        })

    return resultats


def analyser_risque_web(resultats: list[dict]) -> dict:
    """Analyse le niveau de risque basé sur les résultats web.

    Returns:
        Résumé avec niveau de risque.
    """
    if not resultats or "erreur" in resultats[0] or "info" in resultats[0]:
        return {"niveau": "INDÉTERMINÉ", "nb_alertes": 0, "details": "Pas de résultats exploitables."}

    total_alertes = sum(r.get("nb_alertes", 0) for r in resultats)
    mots_uniques = set()
    for r in resultats:
        if r.get("mots_cles_negatifs"):
            mots_uniques.update(r["mots_cles_negatifs"].split(", "))

    if total_alertes == 0:
        niveau = "FAIBLE"
    elif total_alertes <= 3:
        niveau = "MODÉRÉ"
    elif total_alertes <= 8:
        niveau = "ÉLEVÉ"
    else:
        niveau = "TRÈS ÉLEVÉ"

    return {
        "niveau": niveau,
        "nb_alertes": total_alertes,
        "mots_cles_detectes": ", ".join(mots_uniques),
        "nb_resultats_analyses": len(resultats),
    }
