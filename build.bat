@echo off
chcp 65001 > nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo  =========================================
echo   CR Chantier - Build automatique
echo  =========================================
echo.

REM ---- Elevation admin ----
net session >nul 2>&1
if errorlevel 1 (
    echo  Demande des droits administrateur...
    powershell -Command "Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0' -Verb RunAs"
    exit /b
)

REM ---- 1. Trouver Python (hors Microsoft Store) ----
echo [1/4] Verification de Python...

set PYTHON_EXE=

if exist "C:\Program Files\Python311\python.exe" set PYTHON_EXE=C:\Program Files\Python311\python.exe
if exist "C:\Program Files\Python312\python.exe" set PYTHON_EXE=C:\Program Files\Python312\python.exe
if exist "C:\Program Files\Python313\python.exe" set PYTHON_EXE=C:\Program Files\Python313\python.exe
if exist "C:\Python311\python.exe" set PYTHON_EXE=C:\Python311\python.exe
if exist "C:\Python312\python.exe" set PYTHON_EXE=C:\Python312\python.exe

if not "!PYTHON_EXE!"=="" goto :python_ok

REM ---- Python absent : installer via winget ----
echo      Python non detecte. Installation...
winget install Python.Python.3.11 --source winget --scope machine --silent --accept-package-agreements --accept-source-agreements
timeout /t 8 /nobreak >nul

if exist "C:\Program Files\Python311\python.exe" (
    set PYTHON_EXE=C:\Program Files\Python311\python.exe
    goto :python_ok
)

REM ---- Fallback : telechargement direct python.org ----
echo      Telechargement de Python 3.11 depuis python.org...
powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python311_setup.exe' -UseBasicParsing"
if errorlevel 1 (
    echo [ERREUR] Telechargement impossible. Verifiez votre connexion.
    pause & exit /b 1
)
echo      Installation en cours...
"%TEMP%\python311_setup.exe" /quiet InstallAllUsers=1 PrependPath=1 TargetDir=C:\Python311
timeout /t 10 /nobreak >nul
set PYTHON_EXE=C:\Python311\python.exe

:python_ok
if not exist "%PYTHON_EXE%" (
    echo [ERREUR] Python introuvable. Relancez le script.
    pause & exit /b 1
)
echo      OK : %PYTHON_EXE%
"%PYTHON_EXE%" --version

REM ---- 2. Mise a jour pip ----
echo [2/4] Mise a jour de pip...
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet

REM ---- 3. Dependances ----
echo [3/4] Installation des dependances...
"%PYTHON_EXE%" -m pip install flask faster-whisper sounddevice soundfile numpy requests pyinstaller --quiet
if errorlevel 1 (
    echo [ERREUR] Echec installation des dependances.
    pause & exit /b 1
)
echo      OK

REM ---- 4. Build ----
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
echo   Build termine !
echo   Executable : dist\CR_Chantier\CR_Chantier.exe
echo.
echo   Pour distribuer : copier le dossier
echo   dist\CR_Chantier\ en entier.
echo  =========================================
echo.
pause
