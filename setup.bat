@echo off
rem Create a virtual environment in the project folder
python -m venv .venv

rem Activate the virtual environment
call .venv\Scripts\activate.bat

rem Upgrade pip (optional but recommended)
python -m pip install --upgrade pip

rem Install required packages
python -m pip install -r requirements.txt

rem Finished
echo Setup complete. Run "python app.py" to start the proctoring system.
pause
