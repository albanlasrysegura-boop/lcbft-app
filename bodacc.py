"""Module de recherche BODACC (Bulletin Officiel des Annonces Civiles et Commerciales).

Couvre toutes les familles d'annonces :
- Procédures collectives (redressement, liquidation judiciaire)
- Rétablissement professionnel
- Rétablissement personnel (surendettement)
- Créations, radiations, modifications
- Ventes et cessions
- Dépôts des comptes
- Procédures de conciliation
"""

import requests

BODACC_API_BASE = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"

# Familles d'avis disponibles dans le BODACC
FAMILLES_AVIS = [
    "Procédures collectives",
    "Procédures de rétablissement professionnel",
    "Procédures de conciliation",
    "Créations",
    "Immatriculations",
    "Modifications diverses",
    "Radiations",
    "Ventes et cessions",
    "Dépôts des comptes",
    "Annonces diverses",
]


def rechercher_bodacc(
    nom: str,
    limit: int = 20,
    familles: list[str] | None = None,
    inclure_retablissement_personnel: bool = True,
) -> list[dict]:
    """Recherche une personne ou société dans le BODACC.

    Args:
        nom: Nom ou dénomination à rechercher.
        limit: Nombre max de résultats.
        familles: Filtrer par familles d'avis (None = toutes).
        inclure_retablissement_personnel: Inclure une recherche spécifique
            dans le champ jugement pour le rétablissement personnel.

    Returns:
        Liste d'annonces correspondantes.
    """
    nom_escaped = nom.replace('"', '\\"')

    # Recherche principale : nom dans les champs commercant et listepersonnes
    where_parts = [
        f'(commercant like "{nom_escaped}" OR listepersonnes like "{nom_escaped}")',
    ]

    # Filtre par familles d'avis
    if familles:
        famille_clauses = " OR ".join(
            f'familleavis_lib = "{f}"' for f in familles
        )
        where_parts.append(f"({famille_clauses})")

    where_clause = " AND ".join(where_parts)

    resultats = _executer_requete(where_clause, limit)

    # Recherche complémentaire spécifique au rétablissement personnel
    # (ces annonces mentionnent souvent le nom dans le jugement uniquement)
    if inclure_retablissement_personnel:
        where_retab = (
            f'jugement like "{nom_escaped}" '
            f'AND jugement like "rétablissement personnel"'
        )
        resultats_retab = _executer_requete(where_retab, limit)

        # Fusionner sans doublons (par numéro d'annonce)
        ids_existants = {r.get("id") for r in resultats}
        for r in resultats_retab:
            if r.get("id") not in ids_existants:
                r["retablissement_personnel"] = True
                resultats.append(r)

    return resultats


def _executer_requete(where_clause: str, limit: int) -> list[dict]:
    """Exécute une requête sur l'API BODACC OpenDataSoft."""
    params = {
        "where": where_clause,
        "limit": min(limit, 100),
        "order_by": "dateparution DESC",
    }

    try:
        response = requests.get(BODACC_API_BASE, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return [{"erreur": f"Erreur API BODACC : {e}"}]

    resultats = []
    for record in data.get("results", []):
        # Analyser le champ jugement pour détecter le type de procédure
        jugement_raw = record.get("jugement", "") or ""
        jugement_str = str(jugement_raw)

        est_retab_perso = "rétablissement personnel" in jugement_str.lower()
        est_retab_pro = "rétablissement professionnel" in jugement_str.lower()

        # Extraire la nature du jugement depuis le JSON embarqué
        nature_jugement = ""
        if isinstance(jugement_raw, dict):
            nature_jugement = jugement_raw.get("nature", "")
        elif isinstance(jugement_raw, str) and '"nature"' in jugement_raw:
            import json
            try:
                j = json.loads(jugement_raw)
                nature_jugement = j.get("nature", "")
            except (json.JSONDecodeError, TypeError):
                nature_jugement = ""

        resultats.append({
            "id": record.get("id", ""),
            "date_parution": record.get("dateparution", ""),
            "type_avis": record.get("typeavis_lib", ""),
            "famille_avis": record.get("familleavis_lib", ""),
            "commercant": record.get("commercant", ""),
            "tribunal": record.get("tribunal", ""),
            "ville": record.get("ville", ""),
            "code_postal": record.get("cp", ""),
            "departement": record.get("departement_nom_officiel", ""),
            "numero_annonce": record.get("numeroannonce", ""),
            "registre": record.get("registre", ""),
            "nature_jugement": nature_jugement,
            "personnes": record.get("listepersonnes", ""),
            "etablissements": record.get("listeetablissements", ""),
            "retablissement_personnel": est_retab_perso,
            "retablissement_professionnel": est_retab_pro,
            "procedure": (
                "Rétablissement personnel" if est_retab_perso
                else "Rétablissement professionnel" if est_retab_pro
                else record.get("familleavis_lib", "")
            ),
        })

    return resultats


def rechercher_bodacc_multi(
    noms: list[str],
    limit_par_nom: int = 10,
    familles: list[str] | None = None,
) -> dict[str, list[dict]]:
    """Recherche plusieurs noms dans le BODACC."""
    return {
        nom: rechercher_bodacc(nom, limit=limit_par_nom, familles=familles)
        for nom in noms
    }
