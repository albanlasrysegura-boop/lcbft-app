"""Module de capture d'écran web et génération PDF.

Utilise Playwright (Chromium headless) pour capturer les pages de résultats
de recherche Google et les convertir en PDF comme preuve de vigilance.
"""

import os
import tempfile
from datetime import datetime
from urllib.parse import quote_plus

from fpdf import FPDF
from playwright.sync_api import sync_playwright


SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), "captures")


def _ensure_dir():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def capturer_recherche_google(
    nom: str,
    termes_complementaires: str = "fraude blanchiment condamnation sanctions",
) -> dict:
    """Capture une screenshot de la recherche Google pour un nom.

    Args:
        nom: Nom à rechercher.
        termes_complementaires: Termes ajoutés à la recherche.

    Returns:
        Dict avec les chemins des fichiers générés.
    """
    _ensure_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nom_safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in nom)[:50]

    query = f'"{nom}" {termes_complementaires}'
    url = f"https://www.google.com/search?q={quote_plus(query)}&hl=fr&num=10"

    screenshot_path = os.path.join(
        SCREENSHOTS_DIR, f"capture_{nom_safe}_{timestamp}.png"
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                locale="fr-FR",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Accepter les cookies Google si le bandeau apparaît
            try:
                page.click('button:has-text("Tout accepter")', timeout=3000)
                page.wait_for_timeout(1000)
            except Exception:
                pass

            # Capture pleine page
            page.screenshot(path=screenshot_path, full_page=True)

            # Récupérer le titre de la page et l'URL finale
            titre_page = page.title()
            url_finale = page.url

            browser.close()

    except Exception as e:
        return {"erreur": f"Erreur capture : {e}"}

    # Générer le PDF
    pdf_path = os.path.join(
        SCREENSHOTS_DIR, f"vigilance_{nom_safe}_{timestamp}.pdf"
    )
    _generer_pdf(screenshot_path, pdf_path, nom, query, url_finale, titre_page)

    return {
        "screenshot": screenshot_path,
        "pdf": pdf_path,
        "query": query,
        "url": url_finale,
        "timestamp": datetime.now().isoformat(),
    }


def capturer_multiple(
    noms: list[str],
    termes_complementaires: str = "fraude blanchiment condamnation sanctions",
) -> list[dict]:
    """Capture les recherches Google pour plusieurs noms.

    Returns:
        Liste de résultats avec chemins des fichiers.
    """
    resultats = []
    for nom in noms:
        res = capturer_recherche_google(nom, termes_complementaires)
        res["nom"] = nom
        resultats.append(res)
    return resultats


def _generer_pdf(
    screenshot_path: str,
    pdf_path: str,
    nom: str,
    query: str,
    url: str,
    titre_page: str,
):
    """Génère un PDF avec la capture d'écran et les métadonnées."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # En-tête
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "LCB-FT - Capture de vigilance web", ln=True, align="C")
    pdf.ln(5)

    # Métadonnées
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Nom recherche : {nom}", ln=True)
    pdf.cell(0, 6, f"Requete : {query}", ln=True)
    pdf.cell(0, 6, f"URL : {url}", ln=True)
    pdf.cell(0, 6, f"Date : {datetime.now().strftime('%d/%m/%Y a %H:%M:%S')}", ln=True)
    pdf.cell(0, 6, f"Page : {titre_page}", ln=True)
    pdf.ln(5)

    # Ligne de séparation
    pdf.set_draw_color(25, 118, 210)
    pdf.set_line_width(0.5)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Insérer la capture d'écran
    if os.path.exists(screenshot_path):
        # Calculer la largeur pour tenir dans la page (marge de 10mm de chaque côté)
        page_width = 190  # A4 = 210mm - 2*10mm marge
        try:
            from PIL import Image
            with Image.open(screenshot_path) as img:
                img_w, img_h = img.size
                ratio = img_h / img_w
                display_width = page_width
                display_height = display_width * ratio

                # Si l'image est très haute, on la découpe sur plusieurs pages
                y_pos = pdf.get_y()
                available_h = 297 - y_pos - 15  # hauteur dispo sur la 1ère page

                if display_height <= available_h:
                    pdf.image(screenshot_path, x=10, w=display_width)
                else:
                    # L'image dépasse → fpdf2 gère automatiquement le débordement
                    pdf.image(screenshot_path, x=10, w=display_width)

        except ImportError:
            # Sans PIL, insérer directement
            pdf.image(screenshot_path, x=10, w=page_width)

    # Pied de page
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(
        0, 5,
        f"Document genere automatiquement le "
        f"{datetime.now().strftime('%d/%m/%Y a %H:%M')} - "
        f"Application LCB-FT Vigilance Client",
        ln=True, align="C",
    )

    pdf.output(pdf_path)


def generer_pdf_complet(captures: list[dict], nom_fichier: str = "") -> str:
    """Génère un PDF unique regroupant toutes les captures.

    Args:
        captures: Liste de résultats de capturer_recherche_google().
        nom_fichier: Nom du fichier de sortie (optionnel).

    Returns:
        Chemin du PDF généré.
    """
    _ensure_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if not nom_fichier:
        nom_fichier = f"rapport_vigilance_web_{timestamp}.pdf"

    pdf_path = os.path.join(SCREENSHOTS_DIR, nom_fichier)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # Page de garde
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 20)
    pdf.ln(40)
    pdf.cell(0, 15, "Rapport de vigilance web", ln=True, align="C")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(0, 10, "LCB-FT - Captures de recherche", ln=True, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(
        0, 8,
        f"Date : {datetime.now().strftime('%d/%m/%Y a %H:%M')}",
        ln=True, align="C",
    )
    pdf.cell(0, 8, f"Nombre de recherches : {len(captures)}", ln=True, align="C")
    pdf.ln(10)

    # Liste des noms
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Personnes / entites recherchees :", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for cap in captures:
        nom = cap.get("nom", "Inconnu")
        pdf.cell(0, 6, f"  - {nom}", ln=True)

    # Pages de captures
    for cap in captures:
        if "erreur" in cap:
            continue

        pdf.add_page()
        nom = cap.get("nom", "Inconnu")

        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, f"Recherche : {nom}", ln=True)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, f"Requete : {cap.get('query', '')}", ln=True)
        pdf.cell(0, 5, f"URL : {cap.get('url', '')}", ln=True)
        pdf.cell(0, 5, f"Date : {cap.get('timestamp', '')}", ln=True)
        pdf.ln(3)

        screenshot = cap.get("screenshot", "")
        if screenshot and os.path.exists(screenshot):
            try:
                pdf.image(screenshot, x=10, w=190)
            except Exception:
                pdf.cell(0, 10, "[Erreur insertion image]", ln=True)

    pdf.output(pdf_path)
    return pdf_path
