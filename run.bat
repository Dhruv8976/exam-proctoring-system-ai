@echo off
rem Activate the virtual environment and run the proctoring app
if not exist .venv\Scripts\activate.bat (
    echo Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat

python app.py
pause
