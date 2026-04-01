"""Application LCB-FT : Recherche BODACC et Gel des avoirs."""

import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

from bodacc import rechercher_bodacc, FAMILLES_AVIS
from gel_avoirs import rechercher_gel_avoirs

# --- Configuration page ---
st.set_page_config(
    page_title="LCB-FT - Recherche Conformité",
    page_icon="🔍",
    layout="wide",
)

# --- Styles ---
st.markdown("""
<style>
    .alerte-gel { background-color: #ff4444; color: #ffffff; padding: 1rem;
                  border-radius: 8px; border-left: 5px solid #b71c1c;
                  margin: 0.5rem 0; font-weight: bold; font-size: 1.1rem; }
    .alerte-retab { background-color: #ff9800; color: #000000; padding: 1rem;
                    border-radius: 8px; border-left: 5px solid #e65100;
                    margin: 0.5rem 0; font-weight: bold; font-size: 1.1rem; }
    .ok-box { background-color: #2e7d32; color: #ffffff; padding: 1rem;
              border-radius: 8px; border-left: 5px solid #1b5e20;
              margin: 0.5rem 0; font-weight: bold; font-size: 1.1rem; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("LCB-FT - Recherche de Conformité")
st.markdown(
    "Recherche automatique dans les bases **BODACC** "
    "(incl. rétablissement personnel) et **Gel des avoirs (DG Trésor)**"
)

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")

    sources = st.multiselect(
        "Sources à interroger",
        ["BODACC", "Gel des avoirs"],
        default=["BODACC", "Gel des avoirs"],
    )

    st.markdown("---")
    st.subheader("Filtres BODACC")

    toutes_familles = st.checkbox("Toutes les familles d'avis", value=True)
    familles_selectionnees = None
    if not toutes_familles:
        familles_selectionnees = st.multiselect(
            "Familles d'avis",
            FAMILLES_AVIS,
            default=[
                "Procédures collectives",
                "Procédures de rétablissement professionnel",
            ],
        )

    bodacc_limit = st.slider("Résultats BODACC max par nom", 5, 100, 20)

    inclure_retab_perso = st.checkbox(
        "Rechercher le rétablissement personnel",
        value=True,
        help="Recherche complémentaire dans les jugements pour détecter "
             "les procédures de rétablissement personnel (surendettement).",
    )

    st.markdown("---")
    st.markdown("### Sources interrogées")
    st.markdown(
        "- **BODACC** : annonces commerciales, procédures collectives, "
        "rétablissement professionnel ET personnel\n"
        "- **Gel des avoirs** : registre national DG Trésor "
        "(sanctions, mesures de gel)"
    )
    st.markdown("---")
    st.caption(f"Dernière utilisation : {datetime.now().strftime('%d/%m/%Y %H:%M')}")


def afficher_resultats_bodacc(resultats: list[dict], nom: str):
    """Affiche les résultats BODACC avec indicateurs visuels."""
    if not resultats:
        st.markdown(
            f'<div class="ok-box">Aucun résultat BODACC pour <b>{nom}</b>.</div>',
            unsafe_allow_html=True,
        )
        return

    if resultats[0].get("erreur"):
        st.error(resultats[0]["erreur"])
        return

    # Séparer les résultats par type
    retab_perso = [r for r in resultats if r.get("retablissement_personnel")]
    retab_pro = [r for r in resultats if r.get("retablissement_professionnel")]
    autres = [r for r in resultats if not r.get("retablissement_personnel")
              and not r.get("retablissement_professionnel")]

    st.success(f"{len(resultats)} résultat(s) BODACC pour **{nom}**")

    # Alertes rétablissement personnel
    if retab_perso:
        st.markdown(
            f'<div class="alerte-retab">'
            f'⚠️ <b>{len(retab_perso)} annonce(s) de RÉTABLISSEMENT PERSONNEL</b> '
            f'(surendettement)</div>',
            unsafe_allow_html=True,
        )
        df_rp = pd.DataFrame(retab_perso)
        cols_rp = [c for c in [
            "date_parution", "procedure", "commercant", "ville",
            "departement", "tribunal", "nature_jugement",
        ] if c in df_rp.columns]
        st.dataframe(df_rp[cols_rp], use_container_width=True)

    # Alertes rétablissement professionnel
    if retab_pro:
        st.markdown(
            f'<div class="alerte-retab">'
            f'⚠️ <b>{len(retab_pro)} annonce(s) de RÉTABLISSEMENT PROFESSIONNEL</b>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Tableau complet
    df = pd.DataFrame(resultats)
    colonnes_affichage = [c for c in [
        "date_parution", "procedure", "type_avis", "famille_avis",
        "commercant", "ville", "departement", "tribunal",
    ] if c in df.columns]

    with st.expander(f"Voir tous les résultats ({len(resultats)})", expanded=not retab_perso):
        st.dataframe(df[colonnes_affichage], use_container_width=True)

    with st.expander("Détails complets (JSON)"):
        st.dataframe(df, use_container_width=True)


def afficher_resultats_gel(resultats: list[dict], nom: str):
    """Affiche les résultats Gel des avoirs avec alertes."""
    if not resultats:
        st.markdown(
            f'<div class="ok-box">Aucune correspondance Gel des avoirs pour '
            f'<b>{nom}</b>.</div>',
            unsafe_allow_html=True,
        )
        return

    if resultats[0].get("erreur"):
        st.error(resultats[0]["erreur"])
        return

    st.markdown(
        f'<div class="alerte-gel">'
        f'🚨 <b>ALERTE : {len(resultats)} correspondance(s) dans le registre '
        f'des GELS DES AVOIRS pour {nom}</b></div>',
        unsafe_allow_html=True,
    )
    df = pd.DataFrame(resultats)
    st.dataframe(df, use_container_width=True)


# --- Onglets ---
tab_simple, tab_batch = st.tabs(["Recherche simple", "Recherche par lot"])

# ==================== RECHERCHE SIMPLE ====================
with tab_simple:
    col1, col2 = st.columns([3, 1])
    with col1:
        nom_recherche = st.text_input(
            "Nom, prénom ou dénomination à rechercher",
            placeholder="Ex: DUPONT Jean, SCI LES OLIVIERS...",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_recherche = st.button("Rechercher", type="primary", use_container_width=True)

    if btn_recherche and nom_recherche:
        with st.spinner("Recherche en cours..."):
            if "BODACC" in sources:
                st.subheader("BODACC - Annonces commerciales")
                resultats_bodacc = rechercher_bodacc(
                    nom_recherche,
                    limit=bodacc_limit,
                    familles=familles_selectionnees,
                    inclure_retablissement_personnel=inclure_retab_perso,
                )
                afficher_resultats_bodacc(resultats_bodacc, nom_recherche)

            if "Gel des avoirs" in sources:
                st.subheader("Gel des avoirs - Registre national (DG Trésor)")
                resultats_gel = rechercher_gel_avoirs(nom_recherche)
                afficher_resultats_gel(resultats_gel, nom_recherche)

    elif btn_recherche:
        st.warning("Veuillez saisir un nom à rechercher.")

# ==================== RECHERCHE PAR LOT ====================
with tab_batch:
    st.markdown(
        "Saisissez plusieurs noms (un par ligne) ou importez un fichier Excel/CSV."
    )

    col_input, col_file = st.columns(2)

    with col_input:
        noms_texte = st.text_area(
            "Liste de noms (un par ligne)",
            height=200,
            placeholder="DUPONT Jean\nSCI LES OLIVIERS\nMARTIN Pierre",
        )

    with col_file:
        fichier = st.file_uploader(
            "Ou importer un fichier (Excel/CSV)",
            type=["xlsx", "csv"],
            help="Le fichier doit contenir une colonne 'nom' ou 'Nom'. "
                 "Sinon la première colonne sera utilisée.",
        )

    btn_batch = st.button(
        "Lancer la recherche par lot", type="primary", use_container_width=True
    )

    if btn_batch:
        noms = []

        if noms_texte.strip():
            noms = [n.strip() for n in noms_texte.strip().split("\n") if n.strip()]

        if fichier is not None:
            try:
                if fichier.name.endswith(".csv"):
                    df_import = pd.read_csv(fichier)
                else:
                    df_import = pd.read_excel(fichier)

                col_nom = next(
                    (c for c in df_import.columns if c.lower() == "nom"),
                    df_import.columns[0],
                )
                noms.extend(df_import[col_nom].dropna().astype(str).tolist())
            except Exception as e:
                st.error(f"Erreur lecture fichier : {e}")

        # Dédupliquer en préservant l'ordre
        noms = list(dict.fromkeys(noms))

        if not noms:
            st.warning("Aucun nom à rechercher.")
        else:
            st.info(f"Recherche lancée pour **{len(noms)}** nom(s)...")
            progress = st.progress(0)
            rapport = []

            for i, nom in enumerate(noms):
                progress.progress((i + 1) / len(noms))
                ligne = {"Nom recherché": nom}

                if "BODACC" in sources:
                    res_bodacc = rechercher_bodacc(
                        nom, limit=5,
                        familles=familles_selectionnees,
                        inclure_retablissement_personnel=inclure_retab_perso,
                    )
                    valides = [r for r in res_bodacc if "erreur" not in r]
                    ligne["BODACC - Résultats"] = len(valides)

                    types = set(r.get("famille_avis", "") for r in valides if r.get("famille_avis"))
                    ligne["BODACC - Types"] = ", ".join(types)

                    nb_retab_perso = sum(1 for r in valides if r.get("retablissement_personnel"))
                    nb_retab_pro = sum(1 for r in valides if r.get("retablissement_professionnel"))
                    ligne["Rétab. personnel"] = nb_retab_perso
                    ligne["Rétab. professionnel"] = nb_retab_pro

                if "Gel des avoirs" in sources:
                    res_gel = rechercher_gel_avoirs(nom)
                    nb_gel = len([r for r in res_gel if "erreur" not in r])
                    ligne["Gel des avoirs"] = nb_gel
                    ligne["ALERTE GEL"] = "🚨 OUI" if nb_gel > 0 else "✅ NON"

                rapport.append(ligne)

            progress.empty()

            # --- Rapport ---
            st.subheader("Rapport de recherche LCB-FT")
            df_rapport = pd.DataFrame(rapport)

            def highlight_alertes(row):
                styles = [""] * len(row)
                if row.get("ALERTE GEL") == "🚨 OUI":
                    return ["background-color: #ffe0e0"] * len(row)
                if row.get("Rétab. personnel", 0) > 0:
                    return ["background-color: #fff3e0"] * len(row)
                return styles

            st.dataframe(
                df_rapport.style.apply(highlight_alertes, axis=1),
                use_container_width=True,
            )

            # --- Métriques ---
            cols = st.columns(5)
            cols[0].metric("Noms recherchés", len(noms))

            if "BODACC" in sources:
                total_bodacc = int(df_rapport.get("BODACC - Résultats", pd.Series([0])).sum())
                cols[1].metric("Résultats BODACC", total_bodacc)

                nb_rp = int(df_rapport.get("Rétab. personnel", pd.Series([0])).sum())
                cols[2].metric("Rétab. personnel", nb_rp)

                nb_rpro = int(df_rapport.get("Rétab. professionnel", pd.Series([0])).sum())
                cols[3].metric("Rétab. professionnel", nb_rpro)

            if "Gel des avoirs" in sources:
                alertes_gel = (df_rapport.get("ALERTE GEL", pd.Series([])) == "🚨 OUI").sum()
                cols[4].metric("Alertes Gel", int(alertes_gel))

            # --- Export Excel ---
            st.subheader("Export du rapport")
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_rapport.to_excel(writer, sheet_name="Rapport LCB-FT", index=False)

                # Détails BODACC
                if "BODACC" in sources:
                    all_bodacc = []
                    for nom in noms:
                        res = rechercher_bodacc(
                            nom, limit=5,
                            familles=familles_selectionnees,
                            inclure_retablissement_personnel=inclure_retab_perso,
                        )
                        for r in res:
                            if "erreur" not in r:
                                r["nom_recherche"] = nom
                                all_bodacc.append(r)
                    if all_bodacc:
                        pd.DataFrame(all_bodacc).to_excel(
                            writer, sheet_name="Détails BODACC", index=False
                        )

                # Détails Gel des avoirs
                if "Gel des avoirs" in sources:
                    all_gel = []
                    for nom in noms:
                        res = rechercher_gel_avoirs(nom)
                        for r in res:
                            if "erreur" not in r:
                                r["nom_recherche"] = nom
                                all_gel.append(r)
                    if all_gel:
                        pd.DataFrame(all_gel).to_excel(
                            writer, sheet_name="Détails Gel avoirs", index=False
                        )

            st.download_button(
                label="Télécharger le rapport Excel",
                data=output.getvalue(),
                file_name=f"rapport_lcbft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
