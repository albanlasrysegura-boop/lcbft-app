@echo off
chcp 65001 >nul
title LCB-FT - Recherche de Conformité
echo ===================================================
echo   LCB-FT - Recherche de Conformité
echo   BODACC + Gel des avoirs (DG Trésor)
echo ===================================================
echo.

:: Vérifier Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installé.
    echo Téléchargez-le sur https://www.python.org/downloads/
    echo Cochez "Add Python to PATH" lors de l'installation.
    pause
    exit /b 1
)

:: Installer les dépendances si nécessaire
echo Installation des dépendances...
python -m pip install -q -r "%~dp0requirements.txt"
echo.

:: Lancer l'application
echo Démarrage de l'application...
echo.
echo L'application va s'ouvrir dans votre navigateur.
echo Fermez cette fenêtre pour arrêter l'application.
echo.

start "" http://localhost:8501
python -m streamlit run "%~dp0app.py" --server.port 8501 --server.headless true --browser.gatherUsageStats false

pause
