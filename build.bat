@echo off
chcp 65001 > nul
echo.
echo  CR Chantier — Build EXE
echo  ========================
echo.

:: Vérifie Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable. Installez Python 3.11+.
    pause & exit /b 1
)

:: Installe PyInstaller si absent
echo [1/3] Verification de PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo      Installation de PyInstaller...
    pip install pyinstaller
)

:: Installe les dependances si absentes
echo [2/3] Verification des dependances...
pip install flask faster-whisper sounddevice soundfile numpy requests --quiet

:: Build
echo [3/3] Construction de l'executable...
echo.
pyinstaller cr_chantier.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo [ERREUR] Le build a echoue. Voir les logs ci-dessus.
    pause & exit /b 1
)

echo.
echo  =============================================
echo   Build termine !
echo   Executable : dist\CR_Chantier\CR_Chantier.exe
echo
echo   Pour distribuer : copiez le dossier
echo   dist\CR_Chantier\ en entier sur n'importe
echo   quelle machine Windows.
echo  =============================================
echo.
pause
