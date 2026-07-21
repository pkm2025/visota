@echo off
cd /d C:\mmm\visota
start "" /B .venv\Scripts\uvicorn.exe config.asgi:application --host 0.0.0.0 --port 8903 --reload
