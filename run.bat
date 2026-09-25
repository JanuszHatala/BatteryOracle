@echo off
cd /d "%~dp0"
echo Starting Battery Oracle...

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo Virtual environment not found. Creating .venv...
    python -m venv .venv
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
)

streamlit run app.py %*
if %ERRORLEVEL% NEQ 0 (
    echo Application exited with error code %ERRORLEVEL%.
    pause
)
