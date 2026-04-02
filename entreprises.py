"""Module de recherche entreprises : dirigeants et bénéficiaires effectifs.

Sources :
- API Recherche Entreprises (gouv.fr) : gratuite, sans clé
- API INPI/RNE : bénéficiaires effectifs (nécessite habilitation LCB-FT)
"""

import requests

API_RECHERCHE = "https://recherche-entreprises.api.gouv.fr/search"


def rechercher_entreprise(query: str, page: int = 1, per_page: int = 5) -> list[dict]:
    """Recherche une entreprise par nom ou SIREN.

    Args:
        query: Nom de l'entreprise ou numéro SIREN.
        page: Numéro de page.
        per_page: Résultats par page.

    Returns:
        Liste d'entreprises avec leurs informations.
    """
    params = {"q": query, "page": page, "per_page": per_page}

    try:
        response = requests.get(API_RECHERCHE, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        return [{"erreur": f"Erreur API Recherche Entreprises : {e}"}]

    resultats = []
    for entreprise in data.get("results", []):
        # Extraire les dirigeants
        dirigeants = []
        for d in entreprise.get("dirigeants", []):
            dirigeant = {
                "type": d.get("type_dirigeant", ""),
                "qualite": d.get("qualite", ""),
            }
            if d.get("type_dirigeant") == "personne physique":
                nom = d.get("nom", "")
                prenom = d.get("prenom", "")
                dirigeant["nom_complet"] = f"{prenom} {nom}".strip()
                dirigeant["date_naissance"] = d.get("annee_de_naissance", "")
                dirigeant["nationalite"] = d.get("nationalite", "")
            else:
                dirigeant["nom_complet"] = d.get("denomination", "")
                dirigeant["siren"] = d.get("siren", "")
            dirigeants.append(dirigeant)

        # Siège social
        siege = entreprise.get("siege", {})

        resultats.append({
            "siren": entreprise.get("siren", ""),
            "nom_complet": entreprise.get("nom_complet", ""),
            "nom_raison_sociale": entreprise.get("nom_raison_sociale", ""),
            "nature_juridique": entreprise.get("nature_juridique", ""),
            "categorie_entreprise": entreprise.get("categorie_entreprise", ""),
            "etat_administratif": entreprise.get("etat_administratif", ""),
            "date_creation": entreprise.get("date_creation", ""),
            "activite_principale": siege.get("activite_principale", ""),
            "adresse": siege.get("adresse", ""),
            "code_postal": siege.get("code_postal", ""),
            "commune": siege.get("commune", ""),
            "tranche_effectif": entreprise.get("tranche_effectif_salarie", ""),
            "nombre_etablissements": entreprise.get("nombre_etablissements", 0),
            "dirigeants": dirigeants,
            "nb_dirigeants": len(dirigeants),
            "caractere_employeur": entreprise.get("caractere_employeur", ""),
        })

    return resultats


def extraire_dirigeants(query: str) -> list[dict]:
    """Extrait la liste des dirigeants d'une entreprise.

    Args:
        query: Nom ou SIREN de l'entreprise.

    Returns:
        Liste des dirigeants avec leurs fonctions.
    """
    entreprises = rechercher_entreprise(query, per_page=1)

    if not entreprises or "erreur" in entreprises[0]:
        return entreprises

    entreprise = entreprises[0]
    dirigeants = entreprise.get("dirigeants", [])

    for d in dirigeants:
        d["entreprise"] = entreprise.get("nom_complet", "")
        d["siren_entreprise"] = entreprise.get("siren", "")

    return dirigeants


def rechercher_beneficiaires_effectifs(siren: str, api_key_inpi: str = "") -> list[dict]:
    """Recherche les bénéficiaires effectifs via l'API INPI/RNE.

    L'accès aux bénéficiaires effectifs est restreint depuis juillet 2024
    aux assujettis LCB-FT. Nécessite une clé API INPI.

    Sans clé INPI, retourne les dirigeants comme approximation.

    Args:
        siren: Numéro SIREN de l'entreprise.
        api_key_inpi: Clé API INPI (optionnelle).

    Returns:
        Liste des bénéficiaires effectifs ou dirigeants.
    """
    if api_key_inpi:
        # API INPI RNE pour les bénéficiaires effectifs
        url = f"https://data.inpi.fr/api/companies/{siren}/beneficial-owners"
        headers = {"Authorization": f"Bearer {api_key_inpi}"}

        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()

            resultats = []
            for be in data if isinstance(data, list) else data.get("beneficiaires", []):
                resultats.append({
                    "type": "Bénéficiaire effectif",
                    "nom": be.get("nom", ""),
                    "prenom": be.get("prenom", ""),
                    "date_naissance": be.get("dateNaissance", be.get("date_naissance", "")),
                    "nationalite": be.get("nationalite", ""),
                    "pourcentage_parts": be.get("pourcentageParts", ""),
                    "pourcentage_votes": be.get("pourcentageVotes", ""),
                    "modalite_controle": be.get("modaliteControle", ""),
                    "source": "INPI/RNE",
                })
            return resultats

        except requests.RequestException:
            pass  # Fallback vers les dirigeants

    # Fallback : retourner les dirigeants comme approximation
    dirigeants = extraire_dirigeants(siren)
    if dirigeants and "erreur" not in dirigeants[0]:
        for d in dirigeants:
            d["source"] = "API Entreprises (dirigeants - pas les BE)"
            d["type"] = f"Dirigeant ({d.get('qualite', '')})"
        return dirigeants

    return [{"info": "Bénéficiaires effectifs non disponibles. "
             "Configurez une clé API INPI pour y accéder, "
             "ou consultez data.inpi.fr manuellement."}]
