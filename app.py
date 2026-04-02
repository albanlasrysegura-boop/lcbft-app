"""Application LCB-FT : Vigilance client complète."""

import os
import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

from bodacc import rechercher_bodacc, FAMILLES_AVIS
from gel_avoirs import rechercher_gel_avoirs
from opensanctions import rechercher_opensanctions, rechercher_ppe, rechercher_sanctions
from gafi import verifier_pays_gafi, get_listes_gafi, LISTE_NOIRE, LISTE_GRISE
from entreprises import rechercher_entreprise, rechercher_beneficiaires_effectifs
from recherche_web import rechercher_google, analyser_risque_web
from capture_web import capturer_recherche_google, capturer_multiple, generer_pdf_complet

# --- Configuration page ---
st.set_page_config(
    page_title="LCB-FT - Vigilance Client",
    page_icon="🔍",
    layout="wide",
)

# --- Styles ---
st.markdown("""
<style>
    .alerte-critique { background-color: #d32f2f; color: #ffffff; padding: 1rem;
                       border-radius: 8px; border-left: 5px solid #b71c1c;
                       margin: 0.5rem 0; font-weight: bold; font-size: 1.1rem; }
    .alerte-haute { background-color: #ff9800; color: #000000; padding: 1rem;
                    border-radius: 8px; border-left: 5px solid #e65100;
                    margin: 0.5rem 0; font-weight: bold; font-size: 1.1rem; }
    .alerte-moyenne { background-color: #ffc107; color: #000000; padding: 1rem;
                      border-radius: 8px; border-left: 5px solid #ff8f00;
                      margin: 0.5rem 0; font-weight: bold; }
    .ok-box { background-color: #2e7d32; color: #ffffff; padding: 1rem;
              border-radius: 8px; border-left: 5px solid #1b5e20;
              margin: 0.5rem 0; font-weight: bold; font-size: 1.1rem; }
    .info-box { background-color: #1565c0; color: #ffffff; padding: 1rem;
                border-radius: 8px; border-left: 5px solid #0d47a1;
                margin: 0.5rem 0; }
    .section-header { border-bottom: 2px solid #1976d2; padding-bottom: 0.5rem;
                      margin-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.title("LCB-FT - Vigilance Client")
st.markdown(
    "**BODACC** | **Gel des avoirs** | **Sanctions internationales** | "
    "**PPE** | **GAFI** | **Bénéficiaires effectifs** | **Recherche web**"
)

# --- Sidebar : Configuration ---
with st.sidebar:
    st.header("Configuration")

    st.subheader("Sources")
    src_bodacc = st.checkbox("BODACC", value=True)
    src_gel = st.checkbox("Gel des avoirs (DG Trésor)", value=True)
    src_opensanctions = st.checkbox("OpenSanctions (PPE + Sanctions)", value=True)
    src_gafi = st.checkbox("Vérification pays GAFI", value=True)
    src_entreprise = st.checkbox("Entreprise / Dirigeants / BE", value=True)
    src_web = st.checkbox("Recherche web (adverse media)", value=True)

    st.markdown("---")
    st.subheader("Clés API (optionnelles)")

    api_opensanctions = st.text_input(
        "Clé API OpenSanctions",
        type="password",
        help="Gratuit 30 jours sur opensanctions.org/api",
    )
    api_google = st.text_input(
        "Clé API Google Search",
        type="password",
        help="Optionnel. Sans clé, DuckDuckGo est utilisé.",
    )
    cx_google = st.text_input(
        "Google CX (Search Engine ID)",
        help="ID du moteur de recherche personnalisé Google.",
    )
    api_inpi = st.text_input(
        "Clé API INPI (bénéf. effectifs)",
        type="password",
        help="Pour accéder aux vrais bénéficiaires effectifs.",
    )

    st.markdown("---")
    st.subheader("Paramètres BODACC")
    bodacc_limit = st.slider("Résultats max", 5, 50, 15)
    inclure_retab = st.checkbox("Inclure rétablissement personnel", value=True)

    st.markdown("---")
    listes = get_listes_gafi()
    st.caption(f"Listes GAFI : {listes['date_mise_a_jour']}")
    st.caption(f"Dernière utilisation : {datetime.now().strftime('%d/%m/%Y %H:%M')}")


# === ONGLETS PRINCIPAUX ===
tab_personne, tab_entreprise, tab_batch, tab_gafi = st.tabs([
    "Vigilance Personne",
    "Vigilance Entreprise",
    "Recherche par lot",
    "Listes GAFI",
])


# ==================== VIGILANCE PERSONNE ====================
with tab_personne:
    st.subheader("Recherche de vigilance - Personne physique")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        nom_personne = st.text_input(
            "Nom et prénom",
            placeholder="Ex: DUPONT Jean",
            key="nom_personne",
        )
    with col2:
        pays_personne = st.text_input(
            "Pays / Nationalité",
            placeholder="Ex: France, Liban...",
            key="pays_personne",
        )
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_personne = st.button(
            "Lancer la vigilance", type="primary",
            use_container_width=True, key="btn_personne",
        )

    if btn_personne and nom_personne:
        with st.spinner("Analyse en cours..."):
            alertes_total = 0

            # --- 1. GAFI ---
            if src_gafi and pays_personne:
                st.markdown('<h4 class="section-header">Vérification GAFI</h4>',
                            unsafe_allow_html=True)
                resultat_gafi = verifier_pays_gafi(pays_personne)

                if resultat_gafi["liste"] == "LISTE NOIRE":
                    st.markdown(
                        f'<div class="alerte-critique">🚨 {resultat_gafi["pays"]} — '
                        f'LISTE NOIRE GAFI — {resultat_gafi["description"]}</div>',
                        unsafe_allow_html=True)
                    alertes_total += 3
                elif resultat_gafi["liste"] == "LISTE GRISE":
                    st.markdown(
                        f'<div class="alerte-haute">⚠️ {resultat_gafi["pays"]} — '
                        f'LISTE GRISE GAFI — {resultat_gafi["description"]}</div>',
                        unsafe_allow_html=True)
                    alertes_total += 2
                else:
                    st.markdown(
                        f'<div class="ok-box">✅ {resultat_gafi["pays"]} — '
                        f'Pas sur les listes GAFI</div>',
                        unsafe_allow_html=True)

            # --- 2. Gel des avoirs ---
            if src_gel:
                st.markdown('<h4 class="section-header">Gel des avoirs (DG Trésor)</h4>',
                            unsafe_allow_html=True)
                res_gel = rechercher_gel_avoirs(nom_personne)

                if res_gel and "erreur" not in res_gel[0]:
                    st.markdown(
                        f'<div class="alerte-critique">🚨 {len(res_gel)} correspondance(s) '
                        f'dans le registre des GELS DES AVOIRS</div>',
                        unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame(res_gel), use_container_width=True)
                    alertes_total += len(res_gel) * 3
                elif res_gel and "erreur" in res_gel[0]:
                    st.error(res_gel[0]["erreur"])
                else:
                    st.markdown(
                        '<div class="ok-box">✅ Aucune correspondance Gel des avoirs</div>',
                        unsafe_allow_html=True)

            # --- 3. OpenSanctions (PPE + Sanctions) ---
            if src_opensanctions and api_opensanctions:
                st.markdown(
                    '<h4 class="section-header">Sanctions internationales & PPE '
                    '(OpenSanctions)</h4>', unsafe_allow_html=True)
                res_os = rechercher_opensanctions(nom_personne, api_opensanctions)

                if res_os and "erreur" not in res_os[0]:
                    ppe_list = [r for r in res_os if r.get("ppe")]
                    sanc_list = [r for r in res_os if r.get("sanctionne")]

                    if sanc_list:
                        st.markdown(
                            f'<div class="alerte-critique">🚨 {len(sanc_list)} personne(s) '
                            f'SANCTIONNÉE(S) trouvée(s)</div>',
                            unsafe_allow_html=True)
                        alertes_total += len(sanc_list) * 3

                    if ppe_list:
                        st.markdown(
                            f'<div class="alerte-haute">⚠️ {len(ppe_list)} PPE '
                            f'(Personne Politiquement Exposée) trouvée(s)</div>',
                            unsafe_allow_html=True)
                        alertes_total += len(ppe_list) * 2

                    if not sanc_list and not ppe_list and res_os:
                        st.markdown(
                            f'<div class="alerte-moyenne">ℹ️ {len(res_os)} résultat(s) '
                            f'trouvé(s) (ni sanctionné ni PPE)</div>',
                            unsafe_allow_html=True)

                    if not res_os:
                        st.markdown(
                            '<div class="ok-box">✅ Aucune correspondance '
                            'sanctions/PPE</div>', unsafe_allow_html=True)

                    if res_os:
                        df_os = pd.DataFrame(res_os)
                        cols = [c for c in [
                            "nom", "score", "pays", "ppe", "sanctionne",
                            "topics", "position", "date_naissance",
                        ] if c in df_os.columns]
                        st.dataframe(df_os[cols], use_container_width=True)

                elif res_os and "erreur" in res_os[0]:
                    st.error(res_os[0]["erreur"])
            elif src_opensanctions and not api_opensanctions:
                st.markdown(
                    '<h4 class="section-header">Sanctions internationales & PPE</h4>',
                    unsafe_allow_html=True)
                st.warning(
                    "Clé API OpenSanctions non configurée. "
                    "Renseignez-la dans la barre latérale. "
                    "Essai gratuit 30 jours sur opensanctions.org/api"
                )

            # --- 4. BODACC ---
            if src_bodacc:
                st.markdown('<h4 class="section-header">BODACC</h4>',
                            unsafe_allow_html=True)
                res_bodacc = rechercher_bodacc(
                    nom_personne, limit=bodacc_limit,
                    inclure_retablissement_personnel=inclure_retab,
                )
                if res_bodacc and "erreur" not in res_bodacc[0]:
                    retab_p = [r for r in res_bodacc if r.get("retablissement_personnel")]
                    if retab_p:
                        st.markdown(
                            f'<div class="alerte-haute">⚠️ {len(retab_p)} annonce(s) '
                            f'de RÉTABLISSEMENT PERSONNEL</div>',
                            unsafe_allow_html=True)
                        alertes_total += len(retab_p)

                    st.success(f"{len(res_bodacc)} résultat(s) BODACC")
                    df_b = pd.DataFrame(res_bodacc)
                    cols = [c for c in [
                        "date_parution", "procedure", "commercant",
                        "ville", "departement", "tribunal",
                    ] if c in df_b.columns]
                    with st.expander(f"Détails ({len(res_bodacc)} résultats)"):
                        st.dataframe(df_b[cols], use_container_width=True)
                elif res_bodacc and "erreur" in res_bodacc[0]:
                    st.error(res_bodacc[0]["erreur"])
                else:
                    st.markdown(
                        '<div class="ok-box">✅ Aucun résultat BODACC</div>',
                        unsafe_allow_html=True)

            # --- 5. Recherche web ---
            if src_web:
                st.markdown(
                    '<h4 class="section-header">Recherche web (adverse media)</h4>',
                    unsafe_allow_html=True)
                res_web = rechercher_google(nom_personne, api_google, cx_google)
                analyse = analyser_risque_web(res_web)

                if analyse["niveau"] == "TRÈS ÉLEVÉ":
                    st.markdown(
                        f'<div class="alerte-critique">🚨 Risque web TRÈS ÉLEVÉ — '
                        f'{analyse["nb_alertes"]} alerte(s)</div>',
                        unsafe_allow_html=True)
                    alertes_total += 3
                elif analyse["niveau"] == "ÉLEVÉ":
                    st.markdown(
                        f'<div class="alerte-haute">⚠️ Risque web ÉLEVÉ — '
                        f'{analyse["nb_alertes"]} alerte(s)</div>',
                        unsafe_allow_html=True)
                    alertes_total += 2
                elif analyse["niveau"] == "MODÉRÉ":
                    st.markdown(
                        f'<div class="alerte-moyenne">ℹ️ Risque web MODÉRÉ — '
                        f'{analyse["nb_alertes"]} alerte(s)</div>',
                        unsafe_allow_html=True)
                    alertes_total += 1
                else:
                    st.markdown(
                        f'<div class="ok-box">✅ Risque web {analyse["niveau"]}</div>',
                        unsafe_allow_html=True)

                if res_web and "erreur" not in res_web[0] and "info" not in res_web[0]:
                    with st.expander("Détails recherche web"):
                        st.dataframe(pd.DataFrame(res_web), use_container_width=True)

                # Bouton capture d'écran Google → PDF
                if st.button("Capturer la recherche Google en PDF",
                             key="btn_capture_personne"):
                    with st.spinner("Capture en cours (ouverture navigateur)..."):
                        cap = capturer_recherche_google(nom_personne)
                        if "erreur" in cap:
                            st.error(cap["erreur"])
                        else:
                            st.image(cap["screenshot"],
                                     caption="Capture Google", use_container_width=True)
                            with open(cap["pdf"], "rb") as f:
                                st.download_button(
                                    label="Telecharger le PDF de la capture",
                                    data=f.read(),
                                    file_name=os.path.basename(cap["pdf"]),
                                    mime="application/pdf",
                                )

            # --- SYNTHÈSE ---
            st.markdown("---")
            st.subheader("Synthèse de vigilance")

            if alertes_total == 0:
                st.markdown(
                    '<div class="ok-box" style="font-size:1.3rem;">'
                    '✅ AUCUNE ALERTE — Niveau de risque FAIBLE</div>',
                    unsafe_allow_html=True)
            elif alertes_total <= 3:
                st.markdown(
                    f'<div class="alerte-moyenne" style="font-size:1.3rem;">'
                    f'⚠️ {alertes_total} ALERTE(S) — Niveau de risque MODÉRÉ — '
                    f'Vigilance complémentaire recommandée</div>',
                    unsafe_allow_html=True)
            elif alertes_total <= 8:
                st.markdown(
                    f'<div class="alerte-haute" style="font-size:1.3rem;">'
                    f'⚠️ {alertes_total} ALERTE(S) — Niveau de risque ÉLEVÉ — '
                    f'Vigilance renforcée requise</div>',
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<div class="alerte-critique" style="font-size:1.3rem;">'
                    f'🚨 {alertes_total} ALERTE(S) — Niveau de risque TRÈS ÉLEVÉ — '
                    f'Déclaration de soupçon à envisager</div>',
                    unsafe_allow_html=True)

    elif btn_personne:
        st.warning("Veuillez saisir un nom.")


# ==================== VIGILANCE ENTREPRISE ====================
with tab_entreprise:
    st.subheader("Recherche de vigilance - Personne morale")

    col1, col2 = st.columns([3, 1])
    with col1:
        nom_entreprise = st.text_input(
            "Nom de l'entreprise ou SIREN",
            placeholder="Ex: GOOGLE FRANCE, 443061841...",
            key="nom_entreprise",
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_entreprise = st.button(
            "Lancer la vigilance", type="primary",
            use_container_width=True, key="btn_entreprise",
        )

    if btn_entreprise and nom_entreprise:
        with st.spinner("Analyse en cours..."):

            # --- Informations entreprise ---
            if src_entreprise:
                st.markdown(
                    '<h4 class="section-header">Informations entreprise</h4>',
                    unsafe_allow_html=True)
                res_ent = rechercher_entreprise(nom_entreprise)

                if res_ent and "erreur" not in res_ent[0]:
                    ent = res_ent[0]
                    col_a, col_b, col_c = st.columns(3)
                    col_a.metric("SIREN", ent.get("siren", "N/A"))
                    col_b.metric("État", ent.get("etat_administratif", "N/A"))
                    col_c.metric("Dirigeants", ent.get("nb_dirigeants", 0))

                    st.markdown(f"**{ent.get('nom_complet', '')}** — "
                                f"{ent.get('nature_juridique', '')} — "
                                f"{ent.get('commune', '')} ({ent.get('code_postal', '')})")

                    # Dirigeants
                    if ent.get("dirigeants"):
                        st.markdown("**Dirigeants :**")
                        df_dir = pd.DataFrame(ent["dirigeants"])
                        st.dataframe(df_dir, use_container_width=True)

                    # Bénéficiaires effectifs
                    st.markdown(
                        '<h4 class="section-header">Bénéficiaires effectifs</h4>',
                        unsafe_allow_html=True)
                    siren = ent.get("siren", nom_entreprise)
                    res_be = rechercher_beneficiaires_effectifs(siren, api_inpi)

                    if res_be and "erreur" not in res_be[0] and "info" not in res_be[0]:
                        st.dataframe(pd.DataFrame(res_be), use_container_width=True)
                    elif res_be and "info" in res_be[0]:
                        st.info(res_be[0]["info"])
                    else:
                        st.error(res_be[0].get("erreur", "Erreur"))

                    # Vérifier chaque dirigeant dans les bases
                    st.markdown(
                        '<h4 class="section-header">Contrôle des dirigeants</h4>',
                        unsafe_allow_html=True)
                    for d in ent.get("dirigeants", []):
                        nom_dir = d.get("nom_complet", "")
                        if not nom_dir or d.get("type") != "personne physique":
                            continue

                        with st.expander(f"Contrôle : {nom_dir} ({d.get('qualite', '')})"):
                            # Gel des avoirs
                            if src_gel:
                                r_gel = rechercher_gel_avoirs(nom_dir)
                                if r_gel:
                                    st.markdown(
                                        f'<div class="alerte-critique">🚨 '
                                        f'{nom_dir} — GEL DES AVOIRS</div>',
                                        unsafe_allow_html=True)
                                    st.dataframe(pd.DataFrame(r_gel))
                                else:
                                    st.markdown(f"✅ {nom_dir} — OK Gel des avoirs")

                            # OpenSanctions
                            if src_opensanctions and api_opensanctions:
                                r_os = rechercher_opensanctions(
                                    nom_dir, api_opensanctions, limit=3
                                )
                                ppe = [r for r in r_os if r.get("ppe")]
                                sanc = [r for r in r_os if r.get("sanctionne")]
                                if sanc:
                                    st.markdown(
                                        f'<div class="alerte-critique">🚨 '
                                        f'{nom_dir} — SANCTIONNÉ</div>',
                                        unsafe_allow_html=True)
                                elif ppe:
                                    st.markdown(
                                        f'<div class="alerte-haute">⚠️ '
                                        f'{nom_dir} — PPE</div>',
                                        unsafe_allow_html=True)
                                else:
                                    st.markdown(
                                        f"✅ {nom_dir} — OK Sanctions/PPE")

                elif res_ent and "erreur" in res_ent[0]:
                    st.error(res_ent[0]["erreur"])
                else:
                    st.info("Aucune entreprise trouvée.")

            # --- Gel des avoirs (nom entreprise) ---
            if src_gel:
                st.markdown(
                    '<h4 class="section-header">Gel des avoirs (entité)</h4>',
                    unsafe_allow_html=True)
                res_gel = rechercher_gel_avoirs(nom_entreprise)
                if res_gel and "erreur" not in res_gel[0]:
                    st.markdown(
                        f'<div class="alerte-critique">🚨 {len(res_gel)} '
                        f'correspondance(s) GEL DES AVOIRS</div>',
                        unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame(res_gel), use_container_width=True)
                elif res_gel and "erreur" in res_gel[0]:
                    st.error(res_gel[0]["erreur"])
                else:
                    st.markdown(
                        '<div class="ok-box">✅ Aucune correspondance '
                        'Gel des avoirs</div>', unsafe_allow_html=True)

            # --- BODACC ---
            if src_bodacc:
                st.markdown(
                    '<h4 class="section-header">BODACC</h4>',
                    unsafe_allow_html=True)
                res_bodacc = rechercher_bodacc(nom_entreprise, limit=bodacc_limit)
                if res_bodacc and "erreur" not in res_bodacc[0]:
                    st.success(f"{len(res_bodacc)} résultat(s) BODACC")
                    df_b = pd.DataFrame(res_bodacc)
                    cols = [c for c in [
                        "date_parution", "procedure", "commercant",
                        "ville", "tribunal",
                    ] if c in df_b.columns]
                    st.dataframe(df_b[cols], use_container_width=True)
                else:
                    st.markdown(
                        '<div class="ok-box">✅ Aucun résultat BODACC</div>',
                        unsafe_allow_html=True)

            # --- Capture web entreprise ---
            if src_web:
                if st.button("Capturer la recherche Google en PDF",
                             key="btn_capture_entreprise"):
                    with st.spinner("Capture en cours..."):
                        cap = capturer_recherche_google(nom_entreprise)
                        if "erreur" in cap:
                            st.error(cap["erreur"])
                        else:
                            st.image(cap["screenshot"],
                                     caption="Capture Google", use_container_width=True)
                            with open(cap["pdf"], "rb") as f:
                                st.download_button(
                                    label="Telecharger le PDF de la capture",
                                    data=f.read(),
                                    file_name=os.path.basename(cap["pdf"]),
                                    mime="application/pdf",
                                )

    elif btn_entreprise:
        st.warning("Veuillez saisir un nom d'entreprise ou un SIREN.")


# ==================== RECHERCHE PAR LOT ====================
with tab_batch:
    st.subheader("Recherche par lot")
    st.markdown("Saisissez plusieurs noms (un par ligne) ou importez un fichier Excel/CSV.")

    col_input, col_file = st.columns(2)
    with col_input:
        noms_texte = st.text_area(
            "Liste de noms (un par ligne)", height=200,
            placeholder="DUPONT Jean\nSCI LES OLIVIERS\nMARTIN Pierre",
        )
    with col_file:
        fichier = st.file_uploader(
            "Ou importer un fichier (Excel/CSV)",
            type=["xlsx", "csv"],
            help="Colonne 'nom' ou 'Nom', sinon la première colonne.",
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
                df_imp = (pd.read_csv(fichier) if fichier.name.endswith(".csv")
                          else pd.read_excel(fichier))
                col_nom = next(
                    (c for c in df_imp.columns if c.lower() == "nom"),
                    df_imp.columns[0],
                )
                noms.extend(df_imp[col_nom].dropna().astype(str).tolist())
            except Exception as e:
                st.error(f"Erreur lecture fichier : {e}")

        noms = list(dict.fromkeys(noms))

        if not noms:
            st.warning("Aucun nom à rechercher.")
        else:
            st.info(f"Recherche pour **{len(noms)}** nom(s)...")
            progress = st.progress(0)
            rapport = []

            for i, nom in enumerate(noms):
                progress.progress((i + 1) / len(noms))
                ligne = {"Nom recherché": nom}

                if src_gel:
                    r = rechercher_gel_avoirs(nom)
                    nb = len([x for x in r if "erreur" not in x])
                    ligne["Gel avoirs"] = nb
                    ligne["ALERTE GEL"] = "🚨 OUI" if nb > 0 else "✅ NON"

                if src_bodacc:
                    r = rechercher_bodacc(nom, limit=5,
                                         inclure_retablissement_personnel=inclure_retab)
                    valides = [x for x in r if "erreur" not in x]
                    ligne["BODACC"] = len(valides)
                    ligne["Rétab. perso."] = sum(
                        1 for x in valides if x.get("retablissement_personnel"))

                if src_opensanctions and api_opensanctions:
                    r = rechercher_opensanctions(nom, api_opensanctions, limit=5)
                    if r and "erreur" not in r[0]:
                        ligne["PPE"] = sum(1 for x in r if x.get("ppe"))
                        ligne["Sanctionné"] = sum(1 for x in r if x.get("sanctionne"))
                    else:
                        ligne["PPE"] = "—"
                        ligne["Sanctionné"] = "—"

                rapport.append(ligne)

            progress.empty()

            st.subheader("Rapport de recherche LCB-FT")
            df_rapport = pd.DataFrame(rapport)

            def highlight(row):
                if row.get("ALERTE GEL") == "🚨 OUI":
                    return ["background-color: #ffcdd2"] * len(row)
                if row.get("Sanctionné", 0) not in (0, "—") and row.get("Sanctionné", 0) > 0:
                    return ["background-color: #ffcdd2"] * len(row)
                if row.get("PPE", 0) not in (0, "—") and row.get("PPE", 0) > 0:
                    return ["background-color: #fff3e0"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df_rapport.style.apply(highlight, axis=1),
                use_container_width=True,
            )

            # Export Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_rapport.to_excel(writer, sheet_name="Rapport LCB-FT", index=False)

            st.download_button(
                label="Télécharger le rapport Excel",
                data=output.getvalue(),
                file_name=f"rapport_lcbft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


# ==================== LISTES GAFI ====================
with tab_gafi:
    st.subheader("Listes GAFI / FATF")
    listes = get_listes_gafi()
    st.caption(f"Mise à jour : {listes['date_mise_a_jour']} — Source : FATF-GAFI.org")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Liste noire (Appel à l'action)")
        st.markdown("Juridictions à **haut risque**. Contre-mesures recommandées.")
        for pays in LISTE_NOIRE:
            st.markdown(f"- 🚨 **{pays}**")

    with col2:
        st.markdown("### Liste grise (Surveillance renforcée)")
        st.markdown("Juridictions sous **surveillance renforcée**.")
        for pays in LISTE_GRISE:
            st.markdown(f"- ⚠️ {pays}")

    st.markdown("---")
    pays_check = st.text_input("Vérifier un pays", placeholder="Ex: Liban, Iran, France...")
    if pays_check:
        res = verifier_pays_gafi(pays_check)
        if res["liste"] == "LISTE NOIRE":
            st.markdown(
                f'<div class="alerte-critique">🚨 {res["pays"]} — LISTE NOIRE — '
                f'{res["description"]}</div>', unsafe_allow_html=True)
        elif res["liste"] == "LISTE GRISE":
            st.markdown(
                f'<div class="alerte-haute">⚠️ {res["pays"]} — LISTE GRISE — '
                f'{res["description"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(
                f'<div class="ok-box">✅ {res["pays"]} — {res["description"]}</div>',
                unsafe_allow_html=True)
