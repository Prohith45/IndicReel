@echo off
echo ========================================================
echo   Starting IndicReel AI Dubbing Studio (FastAPI)
echo ========================================================
call .\venv\Scripts\activate.bat
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
pause
