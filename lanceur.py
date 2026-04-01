"""Lanceur autonome pour l'application LCB-FT."""

import sys
import os
import subprocess
import webbrowser
import time


def main():
    # Trouver le répertoire de l'application
    if getattr(sys, "frozen", False):
        app_dir = sys._MEIPASS
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))

    app_path = os.path.join(app_dir, "app.py")
    port = 8501

    print("=" * 50)
    print("  LCB-FT - Recherche de Conformité")
    print("  BODACC + Gel des avoirs")
    print("=" * 50)
    print()
    print(f"Démarrage sur http://localhost:{port} ...")
    print("Fermez cette fenêtre pour arrêter l'application.")
    print()

    # Ouvrir le navigateur après un délai
    def open_browser():
        time.sleep(3)
        webbrowser.open(f"http://localhost:{port}")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    # Lancer Streamlit
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", app_path,
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ])


if __name__ == "__main__":
    main()
