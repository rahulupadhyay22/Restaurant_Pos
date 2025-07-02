@echo off
echo ================================
echo   Restaurant POS System Startup
echo ================================

:: Create virtual environment if not exists
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate

:: Install/update dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Reinstall if Flask not available
python -c "import flask" 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Flask not found. Retrying with --no-cache-dir...
    pip install --no-cache-dir -r requirements.txt
)

:: Initialize the database (idempotent)
echo Initializing the database...
python init_db.py

:: Start the POS application
echo Starting the POS server...
python run.py

:: Remove pause for production (avoid hanging window)
REM pause
