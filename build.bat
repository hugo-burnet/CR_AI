@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo  =========================================
echo   CR Chantier - Build automatique
echo  =========================================
echo.

:: ── Elevation admin (necessaire pour installer Python) ────────────────────
net session >nul 2>&1
if errorlevel 1 (
    echo  Demande des droits administrateur...
    powershell -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
)

:: ── 1. Trouver ou installer Python ────────────────────────────────────────
echo [1/4] Verification de Python...

set PYTHON_EXE=

:: Chercher Python dans les emplacements standards (hors Microsoft Store)
for %%P in (
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Program Files\Python310\python.exe"
    "C:\Python311\python.exe"
    "C:\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
) do (
    if exist %%P (
        set PYTHON_EXE=%%~P
        goto :python_ok
    )
)

:: Verifier si python en PATH (et pas le stub Microsoft Store)
where python >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%i in ('python -c "import sys; print(sys.executable)" 2^>nul') do set _PY=%%i
    echo !_PY! | findstr /i "WindowsApps" >nul
    if errorlevel 1 (
        set PYTHON_EXE=!_PY!
        goto :python_ok
    )
)

:: Python absent ou uniquement version Microsoft Store → installer
echo      Python non detecte. Installation via winget...
winget install Python.Python.3.11 --source winget --scope machine --silent --accept-package-agreements --accept-source-agreements >nul 2>&1

:: Attendre que l'installation se termine
timeout /t 5 /nobreak >nul

:: Re-chercher apres installation
for %%P in (
    "C:\Program Files\Python311\python.exe"
    "C:\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) do (
    if exist %%P (
        set PYTHON_EXE=%%~P
        goto :python_ok
    )
)

:: Dernier recours : telechargement direct depuis python.org
echo      Telechargement de Python 3.11 depuis python.org...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python311_setup.exe' -UseBasicParsing"
if errorlevel 1 (
    echo [ERREUR] Impossible de telecharger Python. Verifiez votre connexion internet.
    pause & exit /b 1
)
echo      Installation de Python 3.11...
"%TEMP%\python311_setup.exe" /quiet InstallAllUsers=1 PrependPath=1 TargetDir=C:\Python311
timeout /t 10 /nobreak >nul
set PYTHON_EXE=C:\Python311\python.exe

:python_ok
if not exist "%PYTHON_EXE%" (
    echo [ERREUR] Python introuvable apres installation. Relancez le script.
    pause & exit /b 1
)
echo      OK : %PYTHON_EXE%
"%PYTHON_EXE%" --version

:: ── 2. pip ────────────────────────────────────────────────────────────────
echo [2/4] Mise a jour de pip...
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet

:: ── 3. Dependances ────────────────────────────────────────────────────────
echo [3/4] Installation des dependances (peut prendre quelques minutes)...
"%PYTHON_EXE%" -m pip install flask faster-whisper sounddevice soundfile numpy requests pyinstaller --quiet
if errorlevel 1 (
    echo [ERREUR] Echec installation des dependances.
    pause & exit /b 1
)
echo      OK

:: ── 4. Build PyInstaller ──────────────────────────────────────────────────
echo [4/4] Construction de l'executable...
echo.
"%PYTHON_EXE%" -m PyInstaller cr_chantier.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [ERREUR] Build echoue. Voir les messages ci-dessus.
    pause & exit /b 1
)

echo.
echo  =========================================
echo   Build termine avec succes !
echo.
echo   Executable : dist\CR_Chantier\CR_Chantier.exe
echo.
echo   Pour distribuer l'application, copiez
echo   le dossier dist\CR_Chantier\ en entier.
echo  =========================================
echo.
pause
